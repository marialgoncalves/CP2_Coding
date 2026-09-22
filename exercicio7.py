import os

from flask import (
    Flask,
    render_template_string,
    make_response
)

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

MONGO_COLLECTION = "incidentes"


def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)

    banco = cliente[MONGO_DATABASE]

    return cliente, banco[MONGO_COLLECTION]


def preparar_mongodb():
    cliente, colecao = conectar_mongodb()

    colecao.delete_many({})

    p1 = "<script>alert('xss1')</script>"

    p2 = 'x" onerror="alert(\'xss2\')'

    incidentes = [
        {
            "id": 1,
            "ativo": p1,
            "descricao": "Tentativa de XSS armazenado"
        },
        {
            "id": 2,
            "ativo": p2,
            "descricao": "Tentativa de quebra de atributo HTML"
        }
    ]

    colecao.insert_many(incidentes)

    cliente.close()

    print(
        "[OK] Incidentes de teste cadastrados no MongoDB."
    )


TEMPLATE_SEGURO = """
<!DOCTYPE html>
<html lang="pt-BR">

<head>
    <meta charset="UTF-8">
    <title>Dashboard Seguro</title>
</head>

<body>

    <h1>Dashboard de Segurança</h1>

    <table border="1">

        <tr>
            <th>ID</th>
            <th>Ativo</th>
            <th>Descrição</th>
        </tr>

        {% for evento in eventos %}

        <tr>

            <td>
                {{ evento.id }}
            </td>

            <td>
                {{ evento.ativo }}

                <img
                    src="/icone.png"
                    alt="{{ evento.ativo }}"
                    width="1"
                    height="1"
                >
            </td>

            <td>
                {{ evento.descricao }}
            </td>

        </tr>

        {% endfor %}

    </table>

    <p>
        O uso de |safe neste ponto removeria o escape automático
        do Jinja2 e poderia reabrir a vulnerabilidade de XSS.
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

    <h1>Dashboard Inseguro — comparação</h1>

    <table border="1">

        <tr>
            <th>ID</th>
            <th>Ativo</th>
            <th>Descrição</th>
        </tr>

        {% for evento in eventos %}

        <tr>

            <td>
                {{ evento.id }}
            </td>

            <td>
                {{ evento.ativo|safe }}

                <img
                    src="/icone.png"
                    alt="{{ evento.ativo|safe }}"
                    width="1"
                    height="1"
                >
            </td>

            <td>
                {{ evento.descricao }}
            </td>

        </tr>

        {% endfor %}

    </table>

</body>

</html>
"""


@app.after_request
def adicionar_headers(response):
    response.headers[
        "Content-Security-Policy"
    ] = "default-src 'self'"

    return response


def obter_eventos():
    cliente, colecao = conectar_mongodb()

    eventos = list(
        colecao.find(
            {},
            {
                "_id": 0
            }
        ).sort("id", 1)
    )

    cliente.close()

    return eventos


@app.route("/dashboard")
def dashboard():
    eventos = obter_eventos()

    return render_template_string(
        TEMPLATE_SEGURO,
        eventos=eventos
    )


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    eventos = obter_eventos()

    return render_template_string(
        TEMPLATE_INSEGURO,
        eventos=eventos
    )


@app.route("/icone.png")
def icone():
    response = make_response(
        b"\x89PNG\r\n\x1a\n"
    )

    response.headers[
        "Content-Type"
    ] = "image/png"

    return response


@app.route("/")
def index():
    return """
    <h1>Laboratório de XSS</h1>

    <ul>
        <li>
            <a href="/dashboard">
                Dashboard seguro
            </a>
        </li>

        <li>
            <a href="/dashboard-inseguro">
                Dashboard inseguro
            </a>
        </li>
    </ul>
    """


def executar_testes():
    with app.test_client() as client:

        resposta = client.get(
            "/dashboard"
        )

        conteudo = resposta.get_data(
            as_text=True
        )

        print("=" * 70)
        print("TESTE DO DASHBOARD SEGURO")
        print("=" * 70)

        print(
            "Status:",
            resposta.status_code
        )

        print(
            "CSP:",
            resposta.headers.get(
                "Content-Security-Policy"
            )
        )

        p1 = "<script>alert('xss1')</script>"

        p2 = 'x" onerror="alert(\'xss2\')'

        # O payload original não pode aparecer cru.
        p1_escapado = p1 not in conteudo
        p2_escapado = p2 not in conteudo

        # A tag <script> não pode existir como HTML executável.
        sem_script_executavel = (
            "<script>" not in conteudo
        )

        # O payload que tenta quebrar o atributo
        # precisa estar com as aspas escapadas.
        atributo_protegido = (
            'onerror="alert' not in conteudo
        )

        csp_correta = (
            resposta.headers.get(
                "Content-Security-Policy"
            ) == "default-src 'self'"
        )

        print(
            "p1 protegido:",
            p1_escapado
        )

        print(
            "p2 protegido:",
            p2_escapado
        )

        print(
            "script executável ausente:",
            sem_script_executavel
        )

        print(
            "atributo onerror não criado:",
            atributo_protegido
        )

        print(
            "CSP correta:",
            csp_correta
        )

        assert resposta.status_code == 200
        assert p1_escapado
        assert p2_escapado
        assert sem_script_executavel
        assert atributo_protegido
        assert csp_correta

        print()
        print("[OK] Dashboard seguro aprovado.")


if __name__ == "__main__":
    preparar_mongodb()

    executar_testes()

    app.run(
        host="127.0.0.1",
        port=5007,
        debug=False
    )