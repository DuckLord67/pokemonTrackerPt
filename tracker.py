import os
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

URL = "https://www.fnac.pt/n1012948/Jogos-de-Cartas/Jogos-de-Cartas-Pokemon?SDM=mosaic&SFilt=1!206"
INTERVALO_SEGUNDOS = 60  # Verificação a cada 60 segundos

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

def enviar_alerta(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Secrets do Telegram não detetados.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[!] Erro ao enviar para o Telegram: {e}")

def is_english_box(title: str) -> bool:
    clean = title.lower()
    if not any(w in clean for word in BOX_KEYWORDS):
        return False
    if any(w in clean for word in EXCLUDE_TERMS):
        return False
    return True

def verificar_ronda(session):
    hora = time.strftime("%H:%M:%S")
    try:
        # impersonate="chrome124" mascara o pedido com TLS idêntico ao Chrome de desktop
        res = session.get(URL, headers=HEADERS, impersonate="chrome124", timeout=20)
    except Exception as e:
        print(f"[{hora}] Falha de rede: {e}")
        return

    if res.status_code == 403 or "temporariamente restrito" in res.text:
        print(f"[{hora}] ⚠️ IP do runner temporariamente condicionado pelo WAF.")
        return

    if res.status_code != 200:
        print(f"[{hora}] Resposta inesperada: status {res.status_code}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    articles = soup.find_all("article")
    if not articles:
        articles = soup.find_all("div", class_=re.compile(r"Article-itemGroup|f-search__item", re.I))

    total = len(articles)
    if total == 0:
        print(f"[{hora}] Aviso: 0 artigos lidos no catálogo.")
        return

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
        print(f"[{hora}] 🚨 PRODUTO ENCONTRADO! A notificar Telegram...")
        texto = "🔥 <b>STOCK ENCONTRADO NA FNAC!</b>\n\n"
        for prod in encontrados:
            texto += f"📦 <b>{prod[0]}</b>\n💰 {prod[1]}\n🔗 {prod[2]}\n\n"
        enviar_alerta(texto)
    else:
        print(f"[{hora}] Ronda concluída: {total} artigos analisados. Nenhuma caixa em stock.")

def main():
    print("[+] A iniciar sessão contínua na Cloud...")
    enviar_alerta("🚀 Bot Fnac Contínuo (1 min) iniciado no GitHub Actions!")
    
    session = requests.Session()
    # O job corre durante 5 horas (~300 rondas de 60 segundos)
    limite_rondas = 300 
    ronda = 0

    while ronda < limite_rondas:
        verificar_ronda(session)
        ronda += 1
        time.sleep(INTERVALO_SEGUNDOS)

    print("[+] Limite de ciclo atingido. A renovar instância...")

if __name__ == "__main__":
    main()
