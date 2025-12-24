def processar_modo_vendedor(from_number, metadata, message_payload, cliente, produtos_cliente, menu_items_cliente):
    # --- 0. VERIFICAÇÃO DE PLANO ---
    plano_atual = cliente.get('plano', 'basic')
    if plano_atual != 'full':
        return 

    client_ai = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

    # ==============================================================================
    # 1. EXTRAÇÃO ROBUSTA 
    # ==============================================================================
    texto_msg = message_payload.get("body_text_extracted")
    tipo_midia_app = message_payload.get("media_type")
    wamid = message_payload.get("data", {}).get("wamid") or message_payload.get("messageId")
    push_name = message_payload.get("push_name") or ""

    if texto_msg is None and not tipo_midia_app:
         t_raw, _, _ = _extrair_conteudo_mensagem(message_payload)
         texto_msg = t_raw

    if check_and_set_wamid(wamid): return

    # ==============================================================================
    # 2. REGRAS E LINKS
    # ==============================================================================
    regras_vendas = cliente.get('regras_ia_vendas') or ""
    tipo_negocio = cliente.get('tipo_negocio') or 'serviço' 
    checkout_auto = cliente.get('checkout_automatico', False)
    
    config_raw = cliente.get("config_fluxo") or {}
    config_fluxo = json.loads(config_raw) if isinstance(config_raw, str) else config_raw
    textos_prompts = config_fluxo.get("textos_prompts", {})

    # ### <--- NOVO: LEITURA SEGURA DA TEMPERATURA E VOZ DO JSONB ###
    try: 
        temp_criatividade = float(config_fluxo.get('temperature', 0.5))
    except: 
        temp_criatividade = 0.5
    
    voz_ia = config_fluxo.get('openai_voice', 'alloy') 
    # ### -------------------------------------------------------- ###

    # Links
    catalogo_urls = cliente.get("catalogo_URL")
    links_formatados = ""
    url_principal_str = ""

    if catalogo_urls:
        if isinstance(catalogo_urls, str):
            try: catalogo_urls = json.loads(catalogo_urls)
            except: catalogo_urls = {"geral": catalogo_urls}
        
        if isinstance(catalogo_urls, dict):
            for k, v in catalogo_urls.items():
                nome_link = k.replace('_', ' ').upper()
                links_formatados += f"- {nome_link}: {v}\n"
                if not url_principal_str: url_principal_str = str(v)
        else:
            url_principal_str = str(catalogo_urls)
            links_formatados = f"- GERAL: {url_principal_str}\n"

    # Instruções Dinâmicas
    instrucoes_dinamicas_str = ""
    if textos_prompts:
        instrucoes_dinamicas_str += "\n[DIRETRIZES ESPECÍFICAS]:\n"
        for chave, instrucao in textos_prompts.items():
            topico = chave.replace("_instrucao", "").upper().replace("_", " ")
            instrucao_limpa = instrucao.replace("{catalogo_url}", url_principal_str)
            instrucoes_dinamicas_str += f"- SE O ASSUNTO FOR '{topico}': {instrucao_limpa}\n"

    val_min = config_fluxo.get("decoracao_valor_minimo")
    if val_min and "{valor_minimo_reais}" in instrucoes_dinamicas_str:
         instrucoes_dinamicas_str = instrucoes_dinamicas_str.replace("{valor_minimo_reais}", str(val_min))

    # ==============================================================================
    # 3. GESTÃO DE SESSÃO 
    # ==============================================================================
    conversa_id = None
    metadata_conversa = {}
    nome_tratamento = None 

    try:
        if push_name:
            cliente_final = get_or_create_cliente_final(cliente['id'], from_number, push_name)
            if cliente_final:
                nome_db = cliente_final.get('nome')
                if nome_db and nome_db not in ["Cliente", "Cliente WhatsApp", from_number]:
                      nome_tratamento = nome_db
                elif push_name:
                      update_nome_cliente_final(cliente_final['id'], push_name)
                      nome_tratamento = push_name

        res = supabase.table('conversas').select('*').eq('cliente_id', cliente['id']).eq('cliente_wa_id', from_number).eq('tipo', 'full_dialogo_aberto').execute()
        if res.data:
            ultima = res.data[0]
            conversa_id = ultima['id']
            metadata_conversa = ultima.get('metadata') or {}
        else:
            r = criar_conversa(cliente["id"], "full_dialogo_aberto", wa_id=from_number)
            conversa_id = r['id']
    except: pass

    def _responder(texto):
        # ### <--- DICA: SE SUA FUNÇÃO SUPORTA ÁUDIO, PODE USAR A VARIAVEL voz_ia AQUI ###
        send_text(from_number, texto, cliente)
        if conversa_id: salvar_mensagem_historico(conversa_id, "assistant", texto)

    # ==============================================================================
    # 4. INPUT E HISTÓRICO
    # ==============================================================================
    url_imagem = None
    if tipo_midia_app == "imagem":
        url_imagem = message_payload.get("media_url")
    elif not tipo_midia_app:
        try:
            img_node = message_payload.get("image", {})
            possible_url = img_node.get("imageUrl") or img_node.get("url")
            if possible_url: url_imagem = possible_url
        except: pass

    texto_final_usuario = texto_msg or ("(Enviei uma imagem)" if url_imagem else "(Mensagem vazia)")
    
    conteudo_usuario = [{"type": "text", "text": texto_final_usuario}]
    if url_imagem:
        conteudo_usuario.append({"type": "image_url", "image_url": {"url": url_imagem}})

    if texto_msg and any(x in _norm(texto_msg) for x in PALAVRAS_DE_FUGA):
        if conversa_id:
            meta = metadata_conversa or {}
            if meta.get('status_pagamento') == 'pendente':
                meta.update({'status_pagamento': None, 'agendamento_pendente_id': None})
                atualizar_status_conversa(conversa_id, metadata=meta)
                metadata_conversa = meta

    if conversa_id: salvar_mensagem_historico(conversa_id, "user", texto_final_usuario)

    historico_db = recuperar_historico_mensagens(conversa_id, limite=6)
    catalogo_str, _, map_prof_ids, map_serv_ids = construir_contexto_ia(cliente['id'], produtos_cliente, supabase)
    hoje_str = datetime.now(FUSO_HORARIO_LOCAL).strftime("%A, %d/%m/%Y")
    
    esperando_pgto = metadata_conversa.get('status_pagamento') == 'pendente'
    valor_sinal = metadata_conversa.get('valor_sinal_esperado', 120.00)

    info_pagamento = ""
    if esperando_pgto:
        info_pagamento = f"🚨 ESTADO: AGUARDANDO COMPROVANTE (R$ {valor_sinal:.2f}). Se receber imagem, valide."

    if tipo_negocio == 'festas':
        tool_desc = "Agenda Salão (obrigatório verificar data) ou cria Orçamento Decoração."
    else:
        tool_desc = "Realiza o agendamento do serviço no sistema."

    # ==============================================================================
    # 7. SYSTEM PROMPT
    # ==============================================================================
    system_prompt = f"""
    Você é o Otti, da {cliente.get('nome_empresa')}.
    {cliente.get('prompt_full', '')}
    
    📅 HOJE: {hoje_str}
    👤 CLIENTE: {nome_tratamento or 'Não identificado'}
    
    [MENSAGEM DO CLIENTE]
    "{texto_final_usuario}"
    
    {instrucoes_dinamicas_str}
    
    🔗 LINKS IMPORTANTES (Envie APENAS O LINK, sem markdown):
    {links_formatados}
    
    CATÁLOGO:
    {catalogo_str}
    
    {info_pagamento}
    
    REGRAS:
    1. Responda curto e vendedor.
    2. Use `realizar_agendamento` para fechar pedidos.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "realizar_agendamento",
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "profissional_nome": {"type": "string"},
                        "servico_nome": {"type": "string"},
                        "data_inicio": {"type": "string"}
                    },
                    "required": ["servico_nome", "data_inicio"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "confirmar_pagamento",
                "description": "Confirma pagamento.",
                "parameters": {
                    "type": "object",
                    "properties": { "valor_lido": {"type": "number"} },
                    "required": ["valor_lido"]
                }
            }
        }
    ]

    # ==============================================================================
    # 9. EXECUÇÃO IA 
    # ==============================================================================
    try:
        msgs = [{"role": "system", "content": system_prompt}] + historico_db
        msgs.append({"role": "user", "content": conteudo_usuario})

        for i_turn in range(2): 
            try:
                # ### <--- NOVO: USO DA TEMPERATURA NO REQUEST ###
                resp = client_ai.chat.completions.create(
                    model="gpt-4o", 
                    messages=msgs, 
                    tools=tools, 
                    tool_choice="auto",
                    temperature=temp_criatividade
                )
                # ### ---------------------------------------- ###
            except Exception as e:
                if "image" in str(e):
                    msgs[-1] = {"role": "user", "content": [{"type": "text", "text": f"{texto_final_usuario} (Img Error)"}]}
                    # ### <--- NOVO: USO DA TEMPERATURA NO RETRY ###
                    resp = client_ai.chat.completions.create(
                        model="gpt-4o", 
                        messages=msgs, 
                        tools=tools, 
                        tool_choice="auto", 
                        temperature=temp_criatividade
                    )
                    # ### -------------------------------------- ###
                else: raise e

            msg_ia = resp.choices[0].message
            if not msg_ia.tool_calls:
                _responder(msg_ia.content)
                break 

            msgs.append(msg_ia)
            
            for tool_call in msg_ia.tool_calls:
                fname = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                tool_result_content = ""

                if fname == "realizar_agendamento":
                    nome_prof = args.get('profissional_nome', '').lower()
                    nome_serv = args.get('servico_nome', '')
                    data_raw = args.get('data_inicio')

                    if not data_raw:
                         tool_result_content = "ERRO: Data não fornecida. Pergunte ao cliente."
                    else:
                        try:
                            # 1. Tratamento de Data
                            data_limpa = str(data_raw).replace('T', ' ').replace('Z', '').strip()
                            if len(data_limpa) == 10: data_limpa += " 12:00"
                            dt_inicio = datetime.strptime(data_limpa[:16], "%Y-%m-%d %H:%M")
                            data_reserva_str = dt_inicio.strftime("%Y-%m-%d") 
                            
                            # 2. MATCH INTELIGENTE DIRETO EM produtos_cliente
                            nome_serv_lower = nome_serv.lower()
                            produto_encontrado = None
                            
                            logging.info(f"🔎 [OTTI BUSCA] Negócio: {tipo_negocio} | Busca: {nome_serv_lower} | Data: {data_reserva_str}")

                            if tipo_negocio == 'festas' and ('salão' in nome_serv_lower or 'salao' in nome_serv_lower):
                                # Cálculo de FDS/Semana
                                dia_semana = dt_inicio.weekday() # 0=Seg, 4=Sex
                                eh_fds = dia_semana >= 4
                                quer_sem_decor = 'sem' in nome_serv_lower
                                
                                # Varredura manual na lista de produtos
                                for prod in produtos_cliente:
                                    nome_prod = prod.get('nome', '').lower()
                                    
                                    # Filtro Salão
                                    if 'salão' not in nome_prod and 'salao' not in nome_prod: continue
                                    
                                    # Filtro Decoração (Tem que bater com o pedido)
                                    db_eh_sem = 'sem' in nome_prod
                                    if quer_sem_decor != db_eh_sem: continue 

                                    # Filtro Tempo (FDS vs Semana)
                                    db_eh_fds = 'fds' in nome_prod or 'final' in nome_prod
                                    db_eh_semana = 'semana' in nome_prod
                                    
                                    match_tempo = False
                                    if eh_fds:
                                        if db_eh_fds: match_tempo = True
                                    else:
                                        if db_eh_semana: match_tempo = True
                                    
                                    if match_tempo:
                                        produto_encontrado = prod
                                        break
                            
                            # Se não achou por lógica (ou não é salão), tenta busca padrão pelo nome
                            if not produto_encontrado:
                                for prod in produtos_cliente:
                                    if nome_serv_lower in prod.get('nome', '').lower() or prod.get('nome', '').lower() in nome_serv_lower:
                                        produto_encontrado = prod
                                        break
                            
                            # 3. Definição Final
                            servico_final = {}
                            eh_personalizado = False

                            if produto_encontrado:
                                # Normaliza para o formato padrão do código
                                servico_final = {
                                    'id': produto_encontrado['id'],
                                    'nome': produto_encontrado['nome'],
                                    'preco': 0.0,
                                    'duracao': 60
                                }
                                # CORREÇÃO 2: Parse seguro do regras_preco (Evita erro se já vier dict)
                                try:
                                    rp_raw = produto_encontrado.get('regras_preco', '{}')
                                    if isinstance(rp_raw, dict): rp = rp_raw
                                    else: rp = json.loads(rp_raw)
                                    
                                    servico_final['preco'] = float(rp.get('preco_padrao', 0.0))
                                    servico_final['duracao'] = int(rp.get('duracao_minutos', 60))
                                except: pass
                            else:
                                # Se não achou na lista de produtos
                                if tipo_negocio == 'festas' and 'salão' not in nome_serv_lower:
                                    eh_personalizado = True
                                    servico_final = {'id': 'PERSONALIZADO', 'nome': nome_serv.title(), 'preco': 0.0, 'duracao': 0}
                                else:
                                    # ESSE É O ERRO QUE VOCÊ QUER VER SE FALHAR
                                    msg_erro_logico = f"⚠️ *FALHA DE CATALOGO*\nCliente: {from_number}\nPediu: {nome_serv}\nNão achei ID correspondente em produtos_cliente."
                                    notificar_atendente_async(msg_erro_logico, cliente)
                                    tool_result_content = "ERRO FATAL: Serviço não encontrado."
                                    msgs.append({ "role": "tool", "tool_call_id": tool_call.id, "name": fname, "content": tool_result_content })
                                    continue

                            if servico_final:
                                eh_salao = 'salão' in servico_final['nome'].lower() or 'salao' in servico_final['nome'].lower()
                                
                                deve_salvar_banco = True
                                if eh_personalizado or (tipo_negocio == 'festas' and not eh_salao):
                                    deve_salvar_banco = False
                                
                                # Verifica Disponibilidade (Salao)
                                disponivel = True
                                if deve_salvar_banco and eh_salao and tipo_negocio == 'festas':
                                    try:
                                        res_check = supabase.table('agendamentos_salao').select('id').eq('cliente_id', cliente['id']).neq('status', 'Cancelado').eq('data_reserva', data_reserva_str).execute()
                                        if res_check.data and len(res_check.data) > 0: disponivel = False
                                    except: pass

                                if not disponivel:
                                    tool_result_content = f"DATA INDISPONÍVEL: O salão já está reservado para {dt_inicio.strftime('%d/%m/%Y')}."
                                
                                else:
                                    valor_total = float(servico_final['preco'])
                                    valor_sinal_calc = 0.0
                                    if valor_total > 0:
                                        percentual = float(cliente.get('regra_sinal_percentual', 50)) / 100
                                        valor_sinal_calc = valor_total * percentual
                                        if valor_sinal_calc < 5: valor_sinal_calc = 5

                                    res_db = None
                                    if deve_salvar_banco:
                                        if tipo_negocio == 'festas' and eh_salao:
                                            payload_salao = {
                                                "cliente_id": cliente['id'],
                                                "produto_salao_id": servico_final['id'],
                                                "data_reserva": data_reserva_str,
                                                "status": "Pendente",
                                                "cliente_final_waid": from_number,
                                                "conversa_id_otti": str(conversa_id) if conversa_id else None,
                                                "valor_sinal_registrado": valor_sinal_calc,
                                                "valor_total_registrado": valor_total
                                            }
                                            r_ins = supabase.table('agendamentos_salao').insert(payload_salao).execute()
                                            if r_ins.data: res_db = r_ins.data[0]
                                        else:
                                            # Fluxo Etnia
                                            dt_fim = dt_inicio + timedelta(minutes=servico_final['duracao'])
                                            prof_id = next((pid for n, pid in map_prof_ids.items() if n in nome_prof), list(map_prof_ids.values())[0] if map_prof_ids else None)
                                            payload_db = {
                                                "cliente_id": cliente['id'],
                                                "servico_id": servico_final['id'],
                                                "profissional_id": prof_id,
                                                "cliente_final_waid": from_number,
                                                "data_hora_inicio": dt_inicio.isoformat(),
                                                "data_hora_fim": dt_fim.isoformat(),
                                                "status": "Pendente",
                                                "valor_sinal_registrado": valor_sinal_calc,
                                                "valor_total_registrado": valor_total
                                            }
                                            res_db = inserir_agendamento_real(payload_db)
                                    else:
                                        res_db = {'id': 'ORCAMENTO-ZAP'}

                                    if res_db:
                                        txt_pagamento = ""
                                        if deve_salvar_banco and checkout_auto:
                                            link = gerar_link_universal(valor_sinal_calc, f"AGD-{res_db['id']}", cliente)
                                            if link: txt_pagamento = f"🔗 Link: {link.get('url')}"
                                        
                                        if deve_salvar_banco and not txt_pagamento:
                                            chave_pix = "Chave não configurada"
                                            try:
                                                creds = json.loads(cliente.get("credenciais_pagamento")) if isinstance(cliente.get("credenciais_pagamento"), str) else cliente.get("credenciais_pagamento")
                                                chave_pix = creds.get("pix", {}).get("chave") or chave_pix
                                            except: pass
                                            txt_pagamento = f"🔑 Pix: {chave_pix}"

                                        if eh_personalizado:
                                            _responder(f"Recebi seu pedido para **{servico_final['nome']}** no dia **{dt_inicio.strftime('%d/%m')}**! 🎉\n\nJá notifiquei nossa equipe.")
                                        else:
                                            if deve_salvar_banco:
                                                meta = metadata_conversa or {}
                                                meta.update({'status_pagamento': 'pendente', 'agendamento_pendente_id': res_db['id'], 'valor_sinal_esperado': valor_sinal_calc})
                                                atualizar_status_conversa(conversa_id, metadata=meta)
                                            _responder(f"Combinado! 🎉\n📝 **{servico_final['nome']}**\n📅 **{dt_inicio.strftime('%d/%m/%Y')}**\n💰 Sinal: R$ {valor_sinal_calc:.2f}\n{txt_pagamento}\n\nEnvie o comprovante para confirmar!")

                                        tipo_aviso = "AGENDAMENTO" if deve_salvar_banco else "ORÇAMENTO"
                                        msg_admin = f"🔔 *NOVO {tipo_aviso}*\n👤 {nome_tratamento or from_number}\n🛠️ {servico_final['nome']}\n📅 {dt_inicio.strftime('%d/%m %H:%M')}"
                                        notificar_atendente_async(msg_admin, cliente)
                                        tool_result_content = "SUCESSO."
                                    else:
                                        tool_result_content = "ERRO: Falha ao registrar no banco."

                        except Exception as e_agd:
                            logging.error(f"Erro processamento agenda: {e_agd}")
                            msg_erro = f"⚠️ *FALHA TÉCNICA*\nCliente: {from_number}\nErro: {str(e_agd)}"
                            notificar_atendente_async(msg_erro, cliente)
                            tool_result_content = "ERRO TÉCNICO: Equipe notificada."

                elif fname == "confirmar_pagamento":
                     valor_lido = float(args.get('valor_lido', 0.0))
                     tool_result_content = "SUCESSO: Pagamento confirmado."

                msgs.append({ "role": "tool", "tool_call_id": tool_call.id, "name": fname, "content": tool_result_content })

    except Exception as e:
        logging.error(f"Erro IA Flow: {e}")
        _responder("Tive um problema técnico. Já chamei ajuda!")
