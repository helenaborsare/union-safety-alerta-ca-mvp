"""Gera arquivos FICTICIOS para demonstrar o sistema (pasta demo/).

As datas sao relativas a hoje, entao sempre ha produtos vencidos, a vencer e regulares.
Nada aqui e dado real.
"""
import random
from datetime import date, timedelta
from pathlib import Path

hoje = date.today()
pasta = Path("demo")
pasta.mkdir(exist_ok=True)

# (nome sem o CA, numero do CA, dias ate vencer, situacao na base)
fixos = [
    ("Luva nitrílica tamanho M", 54321, -72, "VENCIDO"),
    ("Protetor auricular plug", 33210, 8, "VÁLIDO"),
    ("Botina usafe bico de aço", 12345, 33, "VÁLIDO"),
    ("Óculos de proteção incolor", 41877, 90, "VÁLIDO"),
    ("Capacete de segurança branco", 20987, 596, "VÁLIDO"),
    ("Luva de vaqueta", 44550, 400, "CANCELADO"),
]
tipos = ["Luva de PVC", "Máscara PFF2", "Protetor facial", "Avental de PVC", "Bota de borracha",
         "Cinto de segurança", "Óculos escuro", "Luva de malha", "Capacete amarelo",
         "Protetor auricular concha", "Respirador semifacial", "Mangote de raspa"]

rnd = random.Random(42)
produtos = []   # (codigo, descricao, estoque)
base = {}       # ca -> (validade, situacao)

for i, (nome, ca, dias, sit) in enumerate(fixos, start=1):
    produtos.append((f"EPI{i:04d}", f"{nome} ca {ca}", rnd.randint(5, 80)))
    base[ca] = (hoje + timedelta(days=dias), sit)
produtos.append(("EPI0100", "Avental de raspa", 12))                 # sem CA
produtos.append(("EPI0101", "Respirador PFF2 ca 99999", 30))         # CA fora da base

for i in range(60):
    ca = 60000 + i
    nome = f"{rnd.choice(tipos)} {rnd.choice(['P', 'M', 'G'])}"
    dias = rnd.choice([-200, -40, 5, 20, 45, 80, 150, 400, 900, 1400])
    produtos.append((f"EPI{200 + i:04d}", f"{nome} ca {ca}", rnd.randint(0, 120)))
    base[ca] = (hoje + timedelta(days=dias), "VÁLIDO" if dias >= 0 else "VENCIDO")
for ca in range(70000, 70400):   # CAs de outros produtos, so para a base ficar maior
    base[ca] = (hoje + timedelta(days=rnd.randint(-900, 1500)), "VÁLIDO")

with open(pasta / "produtos_demo.csv", "w", encoding="utf-8-sig", newline="") as f:
    f.write("Código;Descrição;Estoque\n")
    for cod, desc, est in produtos:
        f.write(f"{cod};{desc};{est}\n")

with open(pasta / "base_ca_demo.csv", "w", encoding="utf-8-sig", newline="") as f:
    f.write("RegistroCA;DataValidade;Situacao\n")
    for ca, (val, sit) in base.items():
        f.write(f"{ca};{val:%d/%m/%Y};{sit}\n")

with open(pasta / "relatorio_falso.csv", "wb") as f:   # para testar a recusa de arquivo invalido
    f.write(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00")

print("Arquivos criados na pasta demo/: produtos_demo.csv, base_ca_demo.csv, relatorio_falso.csv")