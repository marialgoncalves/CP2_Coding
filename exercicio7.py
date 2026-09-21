import os
from flask import Flask, render_template_string, make_response
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

MONGO_DATABASE = os.getenv(
    "MONGO_DATABASE",
    "security_lab"
)


P1 = "<script>alert('xss1')</script>"
P2 = 'x" onerror="alert(\'xss2\')'


def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)
    banco = cliente[MONGO_DATABASE]

    return cliente, banco["incidentes_xss"]


def preparar_dados():
    cliente, colecao = conectar_mongodb()

    colecao.delete_many({})

    colecao.insert_many([
        {
            "titulo": P1,
            "ativo": P1
        },
        {
            "titulo": P2,
            "ativo": P2
        }
    ])

    cliente.close()


TEMPLATE_SEGURO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Dashboard de Incidentes</title>
</head>
<body>

<h1>Dashboard de Incidentes — Seguro</h1>

<table border="1">
    <thead>
        <tr>
            <th>ID</th>
            <th>Título</th>
            <th>Ativo</th>
        </tr>
    </thead>

    <tbody>
        {% for incidente in incidentes %}
        <tr>
            <td>{{ incidente._id }}</td>

            <td>
                {{ incidente.titulo }}
            </td>

            <td>
                <img
                    src="/icone.png"
                    alt="{{ incidente.ativo }}"
                >
                {{ incidente.ativo }}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p>
    Jinja2 faz escape automático do conteúdo inserido no HTML;
    usar <code>|safe</code> indevidamente desativaria esse escape e
    poderia permitir a execução de JavaScript fornecido pelo usuário.
</p>

</body>
</html>
"""


TEMPLATE_INSEGURO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Inseguro</title>
</head>
<body>

<h1>⚠️ DASHBOARD INSEGURO — APENAS PARA COMPARAÇÃO</h1>

<table border="1">
    <thead>
        <tr>
            <th>ID</th>
            <th>Título</th>
            <th>Ativo</th>
        </tr>
    </thead>

    <tbody>
        {% for incidente in incidentes %}
        <tr>
            <td>{{ incidente._id }}</td>

            <td>
                {{ incidente.titulo | safe }}
            </td>

            <td>
                <img
                    src="/icone.png"
                    alt="{{ incidente.ativo | safe }}"
                >
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

</body>
</html>
"""


def resposta_com_csp(conteudo):
    resposta = make_response(conteudo)

    resposta.headers["Content-Security-Policy"] = (
        "default-src 'self'"
    )

    return resposta


@app.route("/dashboard")
def dashboard():
    cliente, colecao = conectar_mongodb()

    incidentes = list(
        colecao.find({})
    )

    cliente.close()

    conteudo = render_template_string(
        TEMPLATE_SEGURO,
        incidentes=incidentes
    )

    return resposta_com_csp(conteudo)


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    cliente, colecao = conectar_mongodb()

    incidentes = list(
        colecao.find({})
    )

    cliente.close()

    conteudo = render_template_string(
        TEMPLATE_INSEGURO,
        incidentes=incidentes
    )

    return resposta_com_csp(conteudo)


@app.route("/icone.png")
def icone():
    resposta = make_response(
        b"\x89PNG\r\n\x1a\n"
    )

    resposta.headers["Content-Type"] = "image/png"

    return resposta_com_csp(resposta)


if __name__ == "__main__":
    preparar_dados()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )