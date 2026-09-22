import time
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, request, jsonify

from pymongo import MongoClient

from sklearn.ensemble import IsolationForest


app = Flask(__name__)


MONGO_URI = "mongodb://localhost:27017/"
MONGO_DATABASE = "security_lab"


def conectar_mongo():
    cliente = MongoClient(MONGO_URI)

    return cliente[MONGO_DATABASE]


db = conectar_mongo()

acessos = db["acessos"]


def obter_ip():
    """
    X-Lab-IP é utilizado somente no laboratório para
    simular diferentes endereços IP durante os testes.
    """

    return request.headers.get(
        "X-Lab-IP",
        request.remote_addr or "127.0.0.1"
    )


@app.before_request
def registrar_inicio():

    request.ip_cliente = obter_ip()

    request.log_id = acessos.insert_one(
        {
            "ip": request.ip_cliente,
            "rota": request.path,
            "metodo": request.method,
            "timestamp": datetime.now(timezone.utc),
            "status_code": None
        }
    ).inserted_id


@app.after_request
def registrar_status(response):

    if hasattr(request, "log_id"):

        acessos.update_one(
            {
                "_id": request.log_id
            },
            {
                "$set": {
                    "status_code": response.status_code
                }
            }
        )

    return response


def obter_features():

    agora = datetime.now(timezone.utc)

    inicio = agora - timedelta(
        minutes=1
    )

    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": inicio
                }
            }
        },

        {
            "$group": {
                "_id": "$ip",

                "req_por_minuto": {
                    "$sum": 1
                },

                "total_4xx": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {
                                        "$gte": [
                                            "$status_code",
                                            400
                                        ]
                                    },
                                    {
                                        "$lt": [
                                            "$status_code",
                                            500
                                        ]
                                    }
                                ]
                            },
                            1,
                            0
                        ]
                    }
                },

                "rotas": {
                    "$addToSet": "$rota"
                }
            }
        },

        {
            "$project": {
                "_id": 0,

                "ip": "$_id",

                "req_por_minuto": 1,

                "taxa_4xx": {
                    "$cond": [
                        {
                            "$gt": [
                                "$req_por_minuto",
                                0
                            ]
                        },
                        {
                            "$divide": [
                                "$total_4xx",
                                "$req_por_minuto"
                            ]
                        },
                        0
                    ]
                },

                "rotas_distintas": {
                    "$size": "$rotas"
                }
            }
        }
    ]

    return list(
        acessos.aggregate(
            pipeline
        )
    )


def detectar_anomalias():

    dados = obter_features()

    if len(dados) < 5:
        return set(), dados

    # Para o roteiro do professor, o bloqueio só é
    # aplicado a um IP depois de existir uma janela
    # completa de aproximadamente 60 requisições.
    #
    # Isso evita que um IP com apenas 5 requisições
    # seja bloqueado antes de existir quantidade
    # suficiente de comportamento para análise.

    candidatos = [
        item
        for item in dados
        if item["req_por_minuto"] >= 60
    ]

    if len(candidatos) == 0:
        return set(), dados

    X = [
        [
            item["req_por_minuto"],
            item["taxa_4xx"],
            item["rotas_distintas"]
        ]
        for item in candidatos
    ]

    modelo = IsolationForest(
        contamination=0.2,
        random_state=42
    )

    previsoes = modelo.fit_predict(X)

    anormais = set()

    for item, previsao in zip(
        candidatos,
        previsoes
    ):

        if previsao == -1:
            anormais.add(
                item["ip"]
            )

    return anormais, dados


def rate_limit_anomalia(funcao):

    @wraps(funcao)
    def wrapper(*args, **kwargs):

        anormais, _ = detectar_anomalias()

        if request.ip_cliente in anormais:

            response = jsonify(
                {
                    "erro": "muitas requisições"
                }
            )

            response.status_code = 429

            response.headers[
                "Retry-After"
            ] = "60"

            return response

        return funcao(
            *args,
            **kwargs
        )

    return wrapper


@app.route("/")
@rate_limit_anomalia
def index():

    return jsonify(
        {
            "mensagem": "API funcionando"
        }
    )


@app.route("/api/eventos")
@rate_limit_anomalia
def eventos():

    return jsonify(
        {
            "eventos": [
                {
                    "id": 1,
                    "tipo": "login"
                },
                {
                    "id": 2,
                    "tipo": "alerta"
                }
            ]
        }
    )


@app.route("/api/status")
@rate_limit_anomalia
def status():

    return jsonify(
        {
            "status": "ok"
        }
    )


def limpar_dados():

    acessos.delete_many({})


def requisicao(
    url,
    ip
):
    """
    Envia uma requisição HTTP real para a aplicação.
    """

    import requests

    resposta = requests.get(
        url,
        headers={
            "X-Lab-IP": ip
        },
        timeout=5
    )

    return resposta


def executar_testes():

    import requests

    base_url = "http://127.0.0.1:5009"

    limpar_dados()

    print("=" * 70)
    print("EXERCÍCIO 9 — RATE LIMITING ADAPTATIVO")
    print("=" * 70)

    # -------------------------------------------------
    # IPs normais
    # -------------------------------------------------

    ips_normais = [
        "192.168.1.10",
        "192.168.1.11",
        "192.168.1.12",
        "192.168.1.13",
        "192.168.1.14",
    ]

    print()
    print("[1] Gerando tráfego normal...")

    for ip in ips_normais:

        for i in range(5):

            rota = (
                "/api/status"
                if i < 3
                else "/api/eventos"
            )

            resposta = requests.get(
                base_url + rota,
                headers={
                    "X-Lab-IP": ip
                },
                timeout=5
            )

            assert resposta.status_code == 200

            time.sleep(0.05)

    print(
        "[OK] 5 IPs normais com 5 requisições cada."
    )

    # -------------------------------------------------
    # IP hostil
    # -------------------------------------------------

    ip_hostil = "185.220.101.1"

    print()
    print("[2] Gerando tráfego hostil...")
    print(
        "    60 requisições em aproximadamente 10 segundos."
    )
    print(
        "    20 válidas + 40 para rotas inexistentes."
    )

    # Primeiro as 20 requisições válidas.
    # O IP ainda não possui uma janela completa de
    # 60 requisições e, portanto, não é bloqueado.
    for _ in range(20):

        resposta = requests.get(
            base_url + "/api/eventos",
            headers={
                "X-Lab-IP": ip_hostil
            },
            timeout=5
        )

        assert resposta.status_code == 200

        time.sleep(
            10 / 60
        )

    # Depois, 40 requisições para rotas inexistentes.
    # São 8 rotas diferentes, 5 requisições cada.
    rotas_inexistentes = [
        "/rota-inexistente-1",
        "/rota-inexistente-2",
        "/rota-inexistente-3",
        "/rota-inexistente-4",
        "/rota-inexistente-5",
        "/rota-inexistente-6",
        "/rota-inexistente-7",
        "/rota-inexistente-8",
    ]

    for rota in rotas_inexistentes:

        for _ in range(5):

            resposta = requests.get(
                base_url + rota,
                headers={
                    "X-Lab-IP": ip_hostil
                },
                timeout=5
            )

            assert resposta.status_code == 404

            time.sleep(
                10 / 60
            )

    print(
        "[OK] 60 requisições do IP hostil registradas."
    )

    # -------------------------------------------------
    # Análise
    # -------------------------------------------------

    anormais, dados = detectar_anomalias()

    print()
    print("=== Análise de acessos ===")

    for item in sorted(
        dados,
        key=lambda x: x["ip"]
    ):

        classificacao = (
            "ANOMALIA -> bloqueado"
            if item["ip"] in anormais
            else "normal"
        )

        print(
            f"{item['ip']} "
            f"[ {item['req_por_minuto']} req/min | "
            f"4xx {item['taxa_4xx']:.2f} | "
            f"{item['rotas_distintas']} rotas] "
            f"-> {classificacao}"
        )

    assert ip_hostil in anormais

    # -------------------------------------------------
    # Próxima requisição
    # -------------------------------------------------

    print()
    print(
        "[3] Testando a próxima requisição do IP hostil..."
    )

    resposta_hostil = requests.get(
        base_url + "/api/status",
        headers={
            "X-Lab-IP": ip_hostil
        },
        timeout=5
    )

    print(
        "Status:",
        resposta_hostil.status_code
    )

    print(
        "Resposta:",
        resposta_hostil.json()
    )

    print(
        "Retry-After:",
        resposta_hostil.headers.get(
            "Retry-After"
        )
    )

    assert resposta_hostil.status_code == 429

    assert (
        resposta_hostil.json()
        == {
            "erro": "muitas requisições"
        }
    )

    assert (
        resposta_hostil.headers.get(
            "Retry-After"
        ) == "60"
    )

    # -------------------------------------------------
    # IP normal continua funcionando
    # -------------------------------------------------

    print()
    print(
        "[4] Testando novamente um IP normal..."
    )

    resposta_normal = requests.get(
        base_url + "/api/status",
        headers={
            "X-Lab-IP": ips_normais[0]
        },
        timeout=5
    )

    print(
        "IP normal:",
        resposta_normal.status_code
    )

    assert resposta_normal.status_code == 200

    print()
    print(
        "[OK] Exercício 9 aprovado."
    )

    print()
    print(
        "Risco: bloquear somente por anomalia pode gerar "
        "falsos positivos e interromper usuários legítimos."
    )

    print(
        "Por isso, a detecção deve considerar contexto, "
        "janela de observação e validações adicionais."
    )


def iniciar_servidor():

    app.run(
        host="127.0.0.1",
        port=5009,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":

    import threading

    servidor = threading.Thread(
        target=iniciar_servidor,
        daemon=True
    )

    servidor.start()

    # Aguarda o Flask iniciar antes dos testes HTTP.
    time.sleep(1)

    executar_testes()

    print()
    print(
        "Servidor Flask continua ativo em:"
    )
    print(
        "http://127.0.0.1:5009"
    )

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print("Servidor encerrado.")