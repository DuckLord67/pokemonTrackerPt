import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.fnac.pt/n1012948/Jogos-de-Cartas/Jogos-de-Cartas-Pokemon?SDM=mosaic&SFilt=1!206"

# Lê as credenciais diretamente dos Secrets protegidos do GitHub
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BOX_KEYWORDS = [
    "booster box", "display", "elite trainer box", "etb", 
    "booster bundle", "collection box", "tin", "lata", "mala", "chest", "caixa"
]

EXCLUDE_TERMS = [
    "japonês", "japones", "japanese", "français", "francês", "alemão",
    "sleeved booster", "checklane", "blister 1 pack", "porta-cartas", 
    "álbum", "caderno", "deck protector", "sleeves", "pasta"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7"
}

def enviar_alerta(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Erro: Secrets do Telegram em falta nas variáveis de ambiente.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao contactar o Telegram: {e}")

def is_english_box(title: str) -> bool:
    clean = title.lower()
    if not any(w in clean for word in BOX_KEYWORDS):
        return False
    if any(w in clean for w in EXCLUDE_TERMS):
        return False
    return True

def run():
    print("[+] A verificar catálogo oficial da Fnac.pt...")
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
    except Exception as e:
        print(f"Erro de rede: {e}")
        return

    if res.status_code != 200:
        print(f"Resposta inesperada do servidor: {res.status_code}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    articles = soup.find_all("article")
    if not articles:
        articles = soup.find_all("div", class_=re.compile(r"Article-itemGroup|f-search__item", re.I))

    print(f"[+] Total de artigos carregados: {len(articles)}")
    encontrados = []

    for item in articles:
        link_tag = item.find("a", class_=re.compile(r"Article-title|title", re.I)) or item.find("a", href=True)
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        link = link_tag.get("href", "")
        if link and not link.startswith("http"):
            link = f"https://www.fnac.pt{link}"

        price_tag = item.find(class_=re.compile(r"userPrice|price", re.I))
        price = price_tag.get_text(strip=True) if price_tag else "Preço n/d"

        if is_english_box(title):
            encontrados.append((title, price, link))

    if encontrados:
        texto = "🔥 <b>STOCK DETETADO NA FNAC!</b>\n\n"
        for prod in encontrados:
            texto += f"📦 <b>{prod[0]}</b>\n💰 {prod[1]}\n🔗 {prod[2]}\n\n"
        enviar_alerta(texto)
        print("[+] Notificação enviada para o teu Telegram!")
    else:
        print("[i] Catálogo verificado: Nenhuma caixa selada em inglês disponível de momento.")

if __name__ == "__main__":
    run()
