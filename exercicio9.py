from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from functools import wraps
from sklearn.ensemble import IsolationForest


app = Flask(__name__)


MONGO_URI = "mongodb://localhost:27017/"
MONGO_DATABASE = "security_lab"


def conectar_mongo():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DATABASE]


db = conectar_mongo()
acessos = db["acessos"]


def obter_ip():
    """
    X-Lab-IP existe apenas para permitir que o teste local
    simule diferentes IPs.
    """
    return request.headers.get(
        "X-Lab-IP",
        request.remote_addr or "127.0.0.1"
    )


@app.before_request
def registrar_inicio():
    request.ip_cliente = obter_ip()

    request.log_id = acessos.insert_one({
        "ip": request.ip_cliente,
        "rota": request.path,
        "metodo": request.method,
        "timestamp": datetime.now(timezone.utc),
        "status_code": None
    }).inserted_id


@app.after_request
def registrar_status(response):
    if hasattr(request, "log_id"):
        acessos.update_one(
            {"_id": request.log_id},
            {"$set": {"status_code": response.status_code}}
        )

    return response


def obter_features():
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(minutes=1)

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

    return list(acessos.aggregate(pipeline))


def detectar_anomalias():
    dados = obter_features()

    if len(dados) < 5:
        return set(), dados

    X = [
        [
            item["req_por_minuto"],
            item["taxa_4xx"],
            item["rotas_distintas"]
        ]
        for item in dados
    ]

    modelo = IsolationForest(
        contamination=0.2,
        random_state=42
    )

    previsoes = modelo.fit_predict(X)

    anormais = set()

    for item, previsao in zip(dados, previsoes):
        if previsao == -1:
            anormais.add(item["ip"])

    return anormais, dados


def rate_limit_anomalia(funcao):
    @wraps(funcao)
    def wrapper(*args, **kwargs):
        anormais, _ = detectar_anomalias()

        if request.ip_cliente in anormais:
            response = jsonify({
                "erro": "IP identificado como comportamento anômalo"
            })

            response.status_code = 429
            response.headers["Retry-After"] = "60"

            return response

        return funcao(*args, **kwargs)

    return wrapper


@app.route("/")
@rate_limit_anomalia
def index():
    return jsonify({
        "mensagem": "API funcionando"
    })


@app.route("/api/eventos")
@rate_limit_anomalia
def eventos():
    return jsonify({
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
    })


@app.route("/api/status")
@rate_limit_anomalia
def status():
    return jsonify({
        "status": "ok"
    })


def limpar_dados():
    acessos.delete_many({})


def simular_acessos(ip, quantidade, rota="/api/eventos"):
    for _ in range(quantidade):
        with app.test_client() as client:
            client.get(
                rota,
                headers={
                    "X-Lab-IP": ip
                }
            )


def mostrar_features():
    _, dados = detectar_anomalias()

    print("\nFEATURES DOS IPs:")

    for item in dados:
        print(
            f"IP: {item['ip']} | "
            f"req/min: {item['req_por_minuto']} | "
            f"taxa_4xx: {item['taxa_4xx']:.2f} | "
            f"rotas distintas: {item['rotas_distintas']}"
        )


def executar_testes():
    limpar_dados()

    print("=" * 60)
    print("EXERCÍCIO 9 — RATE LIMITING ADAPTATIVO")
    print("=" * 60)

    # IPs normais
    simular_acessos(
        "192.168.1.10",
        5,
        "/api/status"
    )

    simular_acessos(
        "192.168.1.11",
        5,
        "/api/eventos"
    )

    simular_acessos(
        "192.168.1.12",
        4,
        "/"
    )

    simular_acessos(
        "192.168.1.13",
        6,
        "/api/status"
    )

    # IP hostil: muitas requisições e várias rotas
    simular_acessos(
        "185.220.101.1",
        60,
        "/api/eventos"
    )

    for rota in [
        "/",
        "/api/status",
        "/api/eventos"
    ]:
        simular_acessos(
            "185.220.101.1",
            20,
            rota
        )

    mostrar_features()

    anormais, _ = detectar_anomalias()

    print("\nIPs classificados como anômalos:")

    for ip in anormais:
        print("-", ip)

    with app.test_client() as client:

        resposta_normal = client.get(
            "/api/status",
            headers={
                "X-Lab-IP": "192.168.1.10"
            }
        )

        print(
            "\nIP normal:",
            resposta_normal.status_code
        )

        resposta_hostil = client.get(
            "/api/status",
            headers={
                "X-Lab-IP": "185.220.101.1"
            }
        )

        print(
            "IP hostil:",
            resposta_hostil.status_code
        )

        if resposta_hostil.status_code == 429:
            print(
                "Retry-After:",
                resposta_hostil.headers.get(
                    "Retry-After"
                )
            )


if __name__ == "__main__":
    executar_testes()

    app.run(
        host="127.0.0.1",
        port=5009,
        debug=False
    )