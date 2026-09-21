import os
import random
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient


# CONFIGURAÇÃO
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

MONGO_DATABASE = os.getenv(
    "MONGO_DATABASE",
    "security_lab"
)

MONGO_COLLECTION = "eventos"

def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)
    banco = cliente[MONGO_DATABASE]
    colecao = banco[MONGO_COLLECTION]

    return cliente, colecao


def criar_indice_ttl(colecao):
    """
    Cria um índice TTL no campo timestamp.

    expireAfterSeconds=604800 representa 7 dias.
    """

    indice = colecao.create_index(
        "timestamp",
        expireAfterSeconds=604800
    )

    return indice


def gerar_eventos(quantidade=200):
    """
    Gera eventos distribuídos aleatoriamente pelas últimas
    24 horas.
    """

    agora = datetime.now(timezone.utc)

    eventos = []

    tipos_falha = [
        "AUTH_FAILURE",
        "BRUTE_FORCE",
        "PORT_SCAN",
        "MALWARE_DETECTED",
        "ACCESS_DENIED",
    ]

    severidades = [
        "baixa",
        "media",
        "alta",
        "critica",
    ]

    for _ in range(quantidade):

        segundos = random.randint(
            0,
            24 * 60 * 60
        )

        timestamp = agora - timedelta(
            seconds=segundos
        )

        evento = {
            "tipo": random.choice(tipos_falha),
            "severidade": random.choice(severidades),
            "timestamp": timestamp,
        }

        eventos.append(evento)

    return eventos



def inserir_eventos(colecao, eventos):
    """
    Remove os dados anteriores e insere os novos eventos.
    """

    colecao.delete_many({})

    resultado = colecao.insert_many(eventos)

    return len(resultado.inserted_ids)


def falhas_por_hora(colecao):
    """
    Agrupa os eventos pelas horas do dia.
    """

    agora = datetime.now(timezone.utc)

    inicio_janela = agora - timedelta(hours=24)

    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": inicio_janela
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$hour": "$timestamp"
                },
                "total": {
                    "$sum": 1
                }
            }
        },
        {
            "$sort": {
                "_id": 1
            }
        }
    ]

    return list(colecao.aggregate(pipeline))


def encontrar_hora_de_pico(distribuicao):
    """
    Encontra a hora que possui maior quantidade de falhas.
    """

    if not distribuicao:
        return None

    return max(
        distribuicao,
        key=lambda item: item["total"]
    )


def criar_barra(total):
    """
    Cria uma representação visual simples da quantidade
    de eventos.
    """

    quantidade_blocos = max(1, total // 2)

    return "█" * quantidade_blocos



def main():

    print("=" * 70)
    print("EXERCÍCIO 3 — RETENÇÃO E JANELA TEMPORAL")
    print("=" * 70)

    # 1. Conexão

    print("\n[1] Conectando ao MongoDB...")

    cliente, colecao = conectar_mongodb()

    print("[OK] Conexão estabelecida.")

    # 2. TTL

    print("\n[2] Criando índice TTL...")

    indice = criar_indice_ttl(colecao)

    print(f"[OK] Índice criado: {indice}")
    print(
        "[OK] Eventos com mais de 7 dias "
        "serão removidos automaticamente."
    )

    # 3. Geração dos eventos

    print("\n[3] Gerando 200 eventos...")

    eventos = gerar_eventos(200)

    print(
        f"[OK] {len(eventos)} eventos gerados "
        "nas últimas 24 horas."
    )

    # 4. Inserção

    print("\n[4] Inserindo eventos no MongoDB...")

    quantidade = inserir_eventos(
        colecao,
        eventos
    )

    print(
        f"[OK] {quantidade} eventos inseridos."
    )

    # 5. Agregação

    print("\n[5] Executando agregação temporal...")

    distribuicao = falhas_por_hora(colecao)

    print("\n=== Falhas por hora (últimas 24h) ===")

    for item in distribuicao:

        hora = item["_id"]
        total = item["total"]

        barra = criar_barra(total)

        print(
            f"{hora:02d}h | "
            f"{barra} {total}"
        )

    # 6. Pico

    pico = encontrar_hora_de_pico(
        distribuicao
    )

    if pico:

        print(
            f"\nHora de pico: "
            f"{pico['_id']:02d}h "
            f"({pico['total']} falhas)"
        )

    else:

        print(
            "\nNenhum evento encontrado."
        )

    # 7. Mensagem sobre TTL

    print(
        "\nÍndice TTL ativo: eventos com mais de "
        "7 dias serão removidos automaticamente."
    )

    print(
        "\nComentário: o TTL é uma decisão de segurança "
        "porque limita a exposição de dados antigos e reduz "
        "a quantidade de informações que um atacante poderia "
        "encontrar caso obtenha acesso ao banco."
    )

    # Encerramento
    
    cliente.close()
