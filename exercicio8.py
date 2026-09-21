import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

app = Flask(__name__)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

MONGO_DATABASE = os.getenv(
    "MONGO_DATABASE",
    "security_lab"
)


X = [
    [0, 1, 1200, 14],
    [1, 1, 1500, 10],
    [0, 2, 2000, 16],
    [2, 2, 3000, 12],
    [1, 3, 4000, 9],
    [0, 1, 1800, 15],
    [2, 1, 2500, 11],
    [1, 2, 3500, 13],
    [0, 1, 1000, 8],
    [2, 3, 5000, 17],

    [12, 7, 90000, 3],
    [15, 8, 120000, 2],
    [10, 6, 85000, 4],
    [20, 10, 150000, 1],
    [8, 7, 95000, 3],
    [14, 9, 110000, 5],
    [11, 8, 100000, 2],
    [18, 12, 200000, 4],
    [9, 6, 80000, 3],
    [16, 10, 140000, 1],
]

y = [
    "baixo",
    "baixo",
    "baixo",
    "baixo",
    "baixo",
    "baixo",
    "baixo",
    "baixo",
    "baixo",
    "baixo",

    "alto",
    "alto",
    "alto",
    "alto",
    "alto",
    "alto",
    "alto",
    "alto",
    "alto",
    "alto",
]

# TREINAMENTO

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y,
)


modelo = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
)


modelo.fit(X_train, y_train)


# MÉTRICAS

def calcular_metricas():
    previsoes = modelo.predict(X_test)

    precisao = precision_score(
        y_test,
        previsoes,
        pos_label="alto",
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        previsoes,
        pos_label="alto",
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        previsoes,
        pos_label="alto",
        zero_division=0,
    )

    matriz = confusion_matrix(
        y_test,
        previsoes,
        labels=["baixo", "alto"],
    )

    return {
        "precisao": round(float(precisao), 2),
        "recall": round(float(recall), 2),
        "f1": round(float(f1), 2),
        "matriz": matriz.tolist(),
    }


def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)

    banco = cliente[MONGO_DATABASE]

    return cliente, banco["previsoes"]


def registrar_previsao(
    entrada,
    risco,
    confianca,
):
    cliente, colecao = conectar_mongodb()

    colecao.insert_one({
        "entrada": entrada,
        "saida": risco,
        "confianca": confianca,
        "timestamp": datetime.now(timezone.utc),
    })

    cliente.close()


# VALIDAÇÃO
def validar_features(dados):
    if not dados or "features" not in dados:
        return None, "corpo da requisição inválido"

    features = dados["features"]

    if not isinstance(features, list):
        return None, "features devem ser uma lista"

    if len(features) != 4:
        return (
            None,
            f"esperadas 4 features, recebidas {len(features)}",
        )

    if not all(
        isinstance(valor, (int, float))
        and not isinstance(valor, bool)
        for valor in features
    ):
        return None, "features devem ser numéricas"

    return features, None


# TRIAGEM

@app.route("/api/triagem", methods=["POST"])
def triagem():

    dados = request.get_json(silent=True)

    features, erro = validar_features(dados)

    if erro:
        return jsonify({
            "erro": erro
        }), 400

    previsao = modelo.predict([features])[0]

    probabilidades = modelo.predict_proba([features])[0]

    classes = list(modelo.classes_)

    indice = classes.index(previsao)

    confianca = float(probabilidades[indice])

    confianca = round(confianca, 2)

    registrar_previsao(
        entrada=features,
        risco=previsao,
        confianca=confianca,
    )

    return jsonify({
        "risco": previsao,
        "confianca": confianca,
    }), 200


@app.route("/api/modelo/metricas", methods=["GET"])
def metricas():

    resultado = calcular_metricas()

    resultado["aviso"] = (
        "A acurácia foi omitida porque pode mascarar erros "
        "importantes quando as classes estão desbalanceadas; "
        "precisão, recall e F1 mostram melhor o comportamento "
        "do modelo na identificação de riscos."
    )

    return jsonify(resultado), 200


# EXECUÇÃO
if __name__ == "__main__":

    cliente, colecao = conectar_mongodb()

    colecao.delete_many({})

    cliente.close()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )