import json
import os
import math
from google.adk.agents import Agent
import webbrowser
import html
import json

# Caminhos dos ficheiros
FICHEIRO_LISTA = "itemList.json"
FICHEIRO_LOCALIZACOES = "productLocation.json"

def guardar_lista_compras(itens: str) -> dict:
    """Cria e guarda uma lista de compras a partir do texto fornecido pelo utilizador, validando com o ficheiro de localizações."""
    if not itens.strip():
        return {
            "status": "error",
            "error_message": "Por favor indica pelo menos um produto para adicionar à lista.",
        }

    # Remove palavras comuns e separa os itens
    stopwords = {"e", "de", "do", "da", "dos", "das", "com", "para", "o", "a", "os", "as", "um", "uma"}
    lista_itens = [
        item.strip().lower()
        for item in itens.replace(",", " ").split()
        if item.strip() and item.lower() not in stopwords
    ]

    # Carrega a base de dados de localizações para validar
    if not os.path.exists(FICHEIRO_LOCALIZACOES):
        return {
            "status": "error",
            "error_message": f"O ficheiro '{FICHEIRO_LOCALIZACOES}' não foi encontrado."
        }

    with open(FICHEIRO_LOCALIZACOES, "r") as f:
        produtos = json.load(f)

    nomes_produtos = [p["nome_produto"].lower() for p in produtos]

    # Validação — só guarda os produtos existentes
    validos = []
    invalidos = []
    for item in lista_itens:
        if any(item in nome for nome in nomes_produtos):
            validos.append(item)
        else:
            invalidos.append(item)

    if not validos:
        return {
            "status": "error",
            "error_message": "Nenhum dos produtos indicados existe na base de dados da loja."
        }

    # Guarda apenas os produtos válidos
    with open(FICHEIRO_LISTA, "w") as f:
        json.dump(validos, f, indent=2, ensure_ascii=False)

    # Mensagem final
    msg = f"Lista guardada com {len(validos)} produto(s): {', '.join(validos)}."
    if invalidos:
        msg += f" ⚠️ Os seguintes produtos não foram encontrados e foram ignorados: {', '.join(invalidos)}."

    return {"status": "success", "report": msg}


def carregar_lista_compras() -> dict:
    """Carrega a lista de compras previamente guardada."""
    if not os.path.exists(FICHEIRO_LISTA):
        return {
            "status": "error",
            "error_message": "Ainda não tens nenhuma lista de compras guardada."
        }

    with open(FICHEIRO_LISTA, "r") as f:
        itens = json.load(f)

    if not itens:
        return {
            "status": "error",
            "error_message": "A tua lista de compras está vazia. Queres criar uma nova?"
        }

    lista_formatada = ", ".join(itens)
    report = f"Aqui está a tua lista atual: {lista_formatada}. Queres gerar a rota?"

    return {
        "status": "success",
        "report": report,
        "itens": itens,
    }


def obter_localizacoes_lista() -> dict:
    """Relaciona os itens da lista de compras com as respetivas localizações na loja."""
    if not os.path.exists(FICHEIRO_LISTA):
        return {"status": "error", "error_message": "Não existe nenhuma lista de compras guardada."}

    if not os.path.exists(FICHEIRO_LOCALIZACOES):
        return {"status": "error", "error_message": f"O ficheiro '{FICHEIRO_LOCALIZACOES}' não foi encontrado."}

    with open(FICHEIRO_LISTA, "r") as f:
        lista_itens = json.load(f)

    with open(FICHEIRO_LOCALIZACOES, "r") as f:
        produtos = json.load(f)

    resultados = []
    for item in lista_itens:
        correspondencias = [p for p in produtos if item.lower() in p["nome_produto"].lower()]
        if correspondencias:
            for p in correspondencias:
                resultados.append({
                    "produto": p["nome_produto"],
                    "corredor": p["corredor"],
                    "secção": p["secção"],
                    "prateleira": p["prateleira"],
                    "caixa": p["caixa"],
                    "coordenada_x": p["coordenada_x"],
                    "coordenada_y": p["coordenada_y"],
                })
        else:
            resultados.append({
                "produto": item,
                "erro": "Produto não encontrado na base de dados de localizações."
            })

    texto = "📍 **Localização dos produtos na loja:**\n\n"
    for r in resultados:
        if "erro" in r:
            texto += f"❌ {r['produto'].capitalize()}: {r['erro']}\n"
        else:
            texto += (
                f"🛒 {r['produto']}\n"
                f"   • Corredor: {r['corredor']}\n"
                f"   • Secção: {r['secção']}\n"
                f"   • Prateleira: {r['prateleira']}\n"
                f"   • Caixa: {r['caixa']}\n"
                f"   • Coordenadas: ({r['coordenada_x']}, {r['coordenada_y']})\n\n"
            )

    return {"status": "success", "report": texto, "resultados": resultados}


def gerar_rota_otimizada() -> dict:
    """Gera uma rota otimizada pela loja com base nas coordenadas dos produtos."""
    # Carrega localizações
    localizacoes = obter_localizacoes_lista()
    if localizacoes["status"] == "error":
        return localizacoes

    produtos = [
        p for p in localizacoes["resultados"]
        if "erro" not in p and "coordenada_x" in p and "coordenada_y" in p
    ]

    if not produtos:
        return {"status": "error", "error_message": "Nenhum produto com coordenadas encontrado."}

    # Heurística simples do caixeiro-viajante (Nearest Neighbor)
    rota = []
    visitados = set()
    atual = produtos[0]
    rota.append(atual)
    visitados.add(atual["produto"])

    while len(visitados) < len(produtos):
        proximos = [
            p for p in produtos if p["produto"] not in visitados
        ]
        if not proximos:
            break

        # Escolhe o produto mais próximo
        proximo = min(
            proximos,
            key=lambda p: math.dist(
                (atual["coordenada_x"], atual["coordenada_y"]),
                (p["coordenada_x"], p["coordenada_y"])
            ),
        )
        rota.append(proximo)
        visitados.add(proximo["produto"])
        atual = proximo

    # Formata a rota
    texto = "🚶 **Rota otimizada dentro da loja:**\n\n"
    for i, p in enumerate(rota, start=1):
        texto += (
            f"{i}. 🛒 {p['produto']}\n"
            f"   → Corredor: {p['corredor']} | Secção: {p['secção']}\n"
            f"   → Coordenadas: ({p['coordenada_x']}, {p['coordenada_y']})\n\n"
        )

    texto += "💡 Dica: segue a ordem acima para percorrer o menor trajeto possível dentro da loja."

    return {"status": "success", "report": texto, "rota": rota}

#adicionei isto novo
def gerar_mapa_html_rota() -> dict:
    """Abre o mapa visual da rota otimizada no servidor local (rota.html)."""
    import webbrowser

    # URL do live server onde o mapa está a correr
    url = "http://127.0.0.1:3000/rota.html"

    try:
        webbrowser.open(url)
        return {
            "status": "success",
            "report": f"🗺️ O mapa visual da rota foi aberto no navegador: {url}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"❌ Ocorreu um erro ao tentar abrir o mapa: {e}"
        }


root_agent = Agent(
    name="assistente_compras",
    model="gemini-2.5-flash",
    description="Assistente de compras automatizado que recebe uma lista de produtos, guarda-a e gera de imediato a rota otimizada no mapa visual da loja..",
    instruction=(
        "És um assistente simpático e eficiente que ajuda o utilizador nas compras dentro da loja.\n\n"
        "🎯 O teu objetivo é perceber o que o utilizador quer fazer e agir de forma natural, SEM passos forçados.\n\n"
        "Comportamento esperado:\n"
        "• Se o utilizador disser apenas 'olá' ou cumprimentar, responde com uma saudação simpática e pergunta se quer ver uma lista existente ou criar uma nova.\n"
        "• Se o utilizador mencionar produtos (ex: 'quero atum e morangos' ou 'adicionar detergente e bacalhau'), chama diretamente 'guardar_lista_compras' com os itens extraídos da frase.\n"
        " - Remove palavras comuns ('e', 'de', 'com', 'para', 'o', 'a', etc.).\n"
        " - Se algum produto não existir, informa de forma breve que foi ignorado.\n"
        "• Depois de guardar, pergunta de forma natural: 'Queres que gere a rota no mapa da loja?'\n"
        "• Se o utilizador responder que sim, chama 'gerar_mapa_html_rota'.\n"
        "• Se o utilizador disser 'usar lista guardada', chama 'carregar_lista_compras' e mostra o conteúdo.\n\n"
        "Estilo de resposta:\n"
        "- Natural, direto e em português de Portugal.\n"
        "- Evita frases longas ou robóticas.\n"
        "- Usa tom humano e positivo, com um emoji simpático ocasional (🛒, 🗺️, ✅).\n"
        "- Não peças confirmação técnica ('quero que execute...'), fala como um assistente real.\n"
        "- Adapta-te: se o utilizador disser algo que mistura intenções (ex: 'gera a rota com os produtos que adicionei ontem'), compreende e age de acordo.\n\n"
        "Exemplos:\n"
        "→ Utilizador: 'olá'\n"
        "→ Tu: 'Olá! 👋 Queres criar uma nova lista de compras ou usar a que já tens guardada?'\n\n"
        "→ Utilizador: 'quero adicionar morangos e bacalhau'\n"
        "→ Tu: 'Lista guardada com 2 produtos: morangos, bacalhau. Queres que gere já a rota no mapa?'\n\n"
        "→ Utilizador: 'sim'\n"
        "→ Tu: '🗺️ A gerar mapa da rota... pronto! Aberto no navegador.'\n\n"
        "→ Utilizador: 'mostra-me a lista que já tenho'\n"
        "→ Tu: 'Aqui está a tua lista atual: atum, leite, pão. Queres gerar a rota?'"
    ),
    tools=[
        guardar_lista_compras,
        carregar_lista_compras,
        obter_localizacoes_lista,
        gerar_rota_otimizada,
        gerar_mapa_html_rota,
    ],
)

