import os
import glob
import re
import gzip
import json
import sys
from lxml import etree

# Pasta onde os seus arquivos XML estão salvos no GitHub
PASTA_LISTAS = "listas/*.xml"

def clean_name(name):
    """Limpa o lixo das listas para sobrar só o nome real"""
    if not name: return ""
    name = name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)|\b(fhd|hd|sd|4k|uhd|h265|hevc|alt|vip)\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    return " ".join(name.split())

def process():
    # 1. Carrega o Cérebro (mapping.json)
    try:
        with open('mapping.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    except Exception as e:
        print(f"Erro ao ler mapping.json: {e}")
        mapping = {}

    # Inverte o mapa para busca rápida: "globo rj" -> "globo.rj"
    reverse_map = {val.lower(): key for key, values in mapping.items() for val in values}

    master_root = etree.Element("tv", {"generator-info-name": "Kron EPG Master"})
    
    canais_adicionados = set()
    programas_adicionados = set() # Evita duplicar o mesmo programa no mesmo horário
    
    # Encontra todos os arquivos .xml na pasta /listas
    arquivos_xml = glob.glob(PASTA_LISTAS)
    
    if not arquivos_xml:
        print("ALERTA CRÍTICO: Nenhum arquivo XML encontrado na pasta /listas!")
        sys.exit(1)

    # 2. Inicia a Varredura e o Merge
    for arquivo in arquivos_xml:
        print(f"Processando arquivo local: {arquivo}")
        try:
            tree = etree.parse(arquivo)

            # --- PROCESSAMENTO DE CANAIS ---
            # Cria um dicionário temporário para saber qual ID original virou qual Master ID neste arquivo
            mapa_ids_locais = {} 

            for channel in tree.xpath("//channel"):
                display_name = channel.findtext("display-name")
                raw_id = channel.get("id")
                
                cleaned = clean_name(display_name)
                # Tenta achar no mapping, se não achar, usa o nome limpo como ID
                final_id = reverse_map.get(cleaned, cleaned.replace(" ", "."))
                
                # Salva a conversão para usar nos programas depois
                mapa_ids_locais[raw_id] = final_id

                # Se o canal ainda não existe no EPG Master, nós adicionamos
                if final_id not in canais_adicionados and final_id != "":
                    channel.set("id", final_id)
                    master_root.append(channel)
                    canais_adicionados.add(final_id)

            # --- PROCESSAMENTO DE PROGRAMAS (A Redundância) ---
            for prog in tree.xpath("//programme"):
                orig_id = prog.get("channel")
                inicio = prog.get("start")
                
                # Descobre qual é o Master ID deste programa
                master_id = mapa_ids_locais.get(orig_id)

                if master_id:
                    # Cria uma "chave única" para não duplicar o mesmo programa
                    chave_prog = f"{master_id}_{inicio}"
                    
                    if chave_prog not in programas_adicionados:
                        prog.set("channel", master_id)
                        master_root.append(prog)
                        programas_adicionados.add(chave_prog)

        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")

    # 3. Salva e Comprime
    if len(canais_adicionados) == 0:
        print("ALERTA CRÍTICO: Nenhum canal processado!")
        sys.exit(1)

    print(f"Merge Concluído! Canais únicos: {len(canais_adicionados)} | Programas únicos: {len(programas_adicionados)}")

    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(etree.tostring(master_root, encoding="utf-8", xml_declaration=True))

if __name__ == "__main__":
    process()import re
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
