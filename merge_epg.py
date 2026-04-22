import os
import glob
import re
import gzip
import json
import sys
from lxml import etree

# Pasta onde os seus arquivos XML/M3U estão salvos no GitHub
PASTA_LISTAS = "listas/*.xml"

def clean_name(name):
    """Limpa o lixo das listas para sobrar só o nome real"""
    if not name: return ""
    name = name.lower()
    name = re.sub(r'\[.*?\]|\(.*?\)|\b(fhd|hd|sd|4k|uhd|h265|hevc|alt|vip)\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    return " ".join(name.split())

def process():
    try:
        with open('mapping.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    except Exception as e:
        print(f"Erro ao ler mapping.json: {e}")
        mapping = {}

    reverse_map = {val.lower(): key for key, values in mapping.items() for val in values}
    master_root = etree.Element("tv", {"generator-info-name": "Kron EPG Master"})
    
    canais_adicionados = set()
    programas_adicionados = set() 
    
    arquivos_xml = glob.glob(PASTA_LISTAS)
    
    if not arquivos_xml:
        print("ALERTA CRÍTICO: Nenhum arquivo XML encontrado na pasta /listas!")
        sys.exit(1)

    for arquivo in arquivos_xml:
        print(f"Processando arquivo local: {arquivo}")
        try:
            tree = etree.parse(arquivo)
            mapa_ids_locais = {} 

            for channel in tree.xpath("//channel"):
                display_name = channel.findtext("display-name")
                raw_id = channel.get("id")
                
                cleaned = clean_name(display_name)
                final_id = reverse_map.get(cleaned, cleaned.replace(" ", "."))
                
                mapa_ids_locais[raw_id] = final_id

                if final_id not in canais_adicionados and final_id != "":
                    channel.set("id", final_id)
                    master_root.append(channel)
                    canais_adicionados.add(final_id)

            for prog in tree.xpath("//programme"):
                orig_id = prog.get("channel")
                inicio = prog.get("start")
                
                master_id = mapa_ids_locais.get(orig_id)

                if master_id:
                    chave_prog = f"{master_id}_{inicio}"
                    if chave_prog not in programas_adicionados:
                        prog.set("channel", master_id)
                        master_root.append(prog)
                        programas_adicionados.add(chave_prog)

        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")

    if len(canais_adicionados) == 0:
        print("ALERTA CRÍTICO: Nenhum canal processado!")
        sys.exit(1)

    print(f"Merge Concluído! Canais únicos: {len(canais_adicionados)} | Programas únicos: {len(programas_adicionados)}")

    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(etree.tostring(master_root, encoding="utf-8", xml_declaration=True))

if __name__ == "__main__":
    process()
