import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request, g
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest

app = Flask(__name__)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

MONGO_DATABASE = os.getenv(
    "MONGO_DATABASE",
    "security_lab"
)


def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)
    banco = cliente[MONGO_DATABASE]

    return cliente, banco["acessos"]


@app.before_request
def registrar_inicio():
    cliente, colecao = conectar_mongodb()

    documento = {
        "ip": request.remote_addr,
        "rota": request.path,
        "metodo": request.method,
        "timestamp": datetime.now(timezone.utc),
    }

    resultado = colecao.insert_one(documento)

    cliente.close()

    g.acesso_id = resultado.inserted_id


@app.after_request
def registrar_status(resposta):
    acesso_id = getattr(g, "acesso_id", None)

    if acesso_id is not None:
        cliente, colecao = conectar_mongodb()

        colecao.update_one(
            {"_id": acesso_id},
            {
                "$set": {
                    "status_code": resposta.status_code
                }
            }
        )

        cliente.close()

    return resposta


# AGREGAÇÃO POR IP
def extrair_features():
    cliente, colecao = conectar_mongodb()

    pipeline = [
        {
            "$group": {
                "_id": "$ip",
                "total_requisicoes": {
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
                "rotas_distintas": {
                    "$addToSet": "$rota"
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "ip": "$_id",
                "req_por_minuto": {
                    "$divide": [
                        "$total_requisicoes",
                        1
                    ]
                },
                "taxa_4xx": {
                    "$cond": [
                        {
                            "$gt": [
                                "$total_requisicoes",
                                0
                            ]
                        },
                        {
                            "$divide": [
                                "$total_4xx",
                                "$total_requisicoes"
                            ]
                        },
                        0
                    ]
                },
                "rotas_distintas": {
                    "$size": "$rotas_distintas"
                }
            }
        }
    ]

    resultados = list(
        colecao.aggregate(pipeline)
    )

    cliente.close()

    return resultados


def analisar_anomalias():
    dados = extrair_features()

    if len(dados) < 2:
        return dados

    X = [
        [
            item["req_por_minuto"],
            item["taxa_4xx"],
            item["rotas_distintas"],
        ]
        for item in dados
    ]

    modelo = IsolationForest(
        contamination=0.2,
        random_state=42
    )

    previsoes = modelo.fit_predict(X)

    for item, previsao in zip(dados, previsoes):
        item["anomalia"] = previsao == -1

    return dados


def ips_bloqueados():
    dados = analisar_anomalias()

    bloqueados = {
        item["ip"]
        for item in dados
        if item.get("anomalia", False)
    }

    return bloqueados


@app.route("/")
def home():
    return jsonify({
        "mensagem": "API funcionando"
    }), 200


@app.route("/api/saude")
def saude():
    return jsonify({
        "status": "ok"
    }), 200


@app.route("/api/dados")
def dados():
    return jsonify({
        "dados": "acesso autorizado"
    }), 200


@app.route("/api/analise")
def analise():
    return jsonify({
        "resultado": "normal"
    }), 200


@app.before_request
def bloquear_anomalia():
    # O registro da requisição acontece antes deste ponto
    # e será completado pelo after_request.

    ip = request.remote_addr

    # Evita tentar analisar enquanto ainda não existem dados
    # suficientes para o IsolationForest.
    dados = extrair_features()

    if len(dados) < 2:
        return None

    X = [
        [
            item["req_por_minuto"],
            item["taxa_4xx"],
            item["rotas_distintas"],
        ]
        for item in dados
    ]

    modelo = IsolationForest(
        contamination=0.2,
        random_state=42
    )

    previsoes = modelo.fit_predict(X)

    for item, previsao in zip(dados, previsoes):
        if (
            item["ip"] == ip
            and previsao == -1
        ):
            resposta = jsonify({
                "erro": "muitas requisições"
            })

            resposta.status_code = 429
            resposta.headers["Retry-After"] = "60"

            return resposta

    return None


# RELATÓRIO
@app.route("/api/anomalias", methods=["GET"])
def relatorio_anomalias():

    dados = analisar_anomalias()

    resultado = []

    for item in dados:
        resultado.append({
            "ip": item["ip"],
            "req_por_minuto": item["req_por_minuto"],
            "taxa_4xx": item["taxa_4xx"],
            "rotas_distintas": item["rotas_distintas"],
            "situacao": (
                "ANOMALIA -> bloqueado"
                if item.get("anomalia", False)
                else "normal"
            )
        })

    return jsonify({
        "analise": resultado,
        "comentario": (
            "Bloquear por anomalia pode gerar falso positivo e "
            "impedir o acesso de um usuário legítimo. "
            "Por isso, o comportamento detectado deve ser analisado "
            "com cuidado antes de aplicar bloqueios automáticos."
        )
    }), 200


if __name__ == "__main__":

    cliente, colecao = conectar_mongodb()

    colecao.delete_many({})

    cliente.close()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )