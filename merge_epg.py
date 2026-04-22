import re
import requests
import gzip
import json
from lxml import etree

# URLs dos XMLs que você me mandou
EPG_SOURCES = [
    "https://raw.githubusercontent.com/limalalef/BrazilTVEPG/main/epg.xml",
    "https://iptv-org.github.io/epg/guides/br.xml"
]

def clean_name(name):
    if not name: return ""
    name = name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)|\b(fhd|hd|sd|4k|uhd|h265|hevc|alt|vip)\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    return " ".join(name.split())

def process():
    try:
        with open('mapping.json', 'r') as f:
            mapping = json.load(f)
    except:
        mapping = {}

    reverse_map = {val: key for key, values in mapping.items() for val in values}
    master_root = etree.Element("tv")
    added_channels = set()

    for url in EPG_SOURCES:
        try:
            print(f"Processando: {url}")
            r = requests.get(url, timeout=30)
            tree = etree.fromstring(r.content)

            for channel in tree.xpath("//channel"):
                display_name = channel.findtext("display-name")
                raw_id = channel.get("id")
                
                cleaned = clean_name(display_name)
                final_id = reverse_map.get(cleaned, reverse_map.get(raw_id, cleaned.replace(" ", ".")))

                if final_id not in added_channels:
                    channel.set("id", final_id)
                    master_root.append(channel)
                    added_channels.add(final_id)

            for prog in tree.xpath("//programme"):
                # Em um cenário real completo, mapeamos o ID do programa aqui
                master_root.append(prog)

        except Exception as e:
            print(f"Erro ao processar {url}: {e}")

    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(etree.tostring(master_root, encoding="utf-8", xml_declaration=True))

if __name__ == "__main__":
    process()
