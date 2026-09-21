from flask import Flask, render_template_string, make_response
from markupsafe import escape


app = Flask(__name__)


EVENTOS = [
    {
        "id": 1,
        "ativo": "<script>alert('xss1')</script>",
        "descricao": "Tentativa de XSS armazenado"
    },
    {
        "id": 2,
        "ativo": 'x" onerror="alert(\'xss2\')',
        "descricao": "Tentativa de quebra de atributo HTML"
    }
]


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
            <td>{{ evento.id }}</td>
            <td>
                {{ evento.ativo }}
                <img
                    src="/icone.png"
                    alt="{{ evento.ativo }}"
                    width="1"
                    height="1"
                >
            </td>
            <td>{{ evento.descricao }}</td>
        </tr>
        {% endfor %}
    </table>
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
            <td>{{ evento.id }}</td>
            <td>
                {{ evento.ativo|safe }}
                <img
                    src="/icone.png"
                    alt="{{ evento.ativo|safe }}"
                    width="1"
                    height="1"
                >
            </td>
            <td>{{ evento.descricao }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""


def resposta_com_csp(html):
    resposta = make_response(html)

    resposta.headers[
        "Content-Security-Policy"
    ] = "default-src 'self'"

    return resposta


@app.after_request
def adicionar_headers(response):
    response.headers[
        "Content-Security-Policy"
    ] = "default-src 'self'"

    return response


@app.route("/dashboard")
def dashboard():
    return render_template_string(
        TEMPLATE_SEGURO,
        eventos=EVENTOS
    )


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    return render_template_string(
        TEMPLATE_INSEGURO,
        eventos=EVENTOS
    )


@app.route("/icone.png")
def icone():
    response = make_response(
        b"\x89PNG\r\n\x1a\n"
    )

    response.headers["Content-Type"] = "image/png"

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

        resposta = client.get("/dashboard")

        conteudo = resposta.get_data(as_text=True)

        print("=" * 60)
        print("TESTE DO DASHBOARD SEGURO")
        print("=" * 60)

        print("Status:", resposta.status_code)

        print(
            "CSP:",
            resposta.headers.get("Content-Security-Policy")
        )

        print(
            "Payload p1 literal:",
            "&lt;script&gt;" in conteudo
        )

        print(
            "Payload p2 escapado:",
            "onerror=" not in conteudo
            or "&#34;" in conteudo
        )

        assert resposta.status_code == 200
        assert (
            resposta.headers.get(
                "Content-Security-Policy"
            ) == "default-src 'self'"
        )


if __name__ == "__main__":
    executar_testes()

    app.run(
        host="127.0.0.1",
        port=5007,
        debug=False
    )