# A função recomendar apenas percorre as regras e aplica a primeira
# que corresponde ao perfil recebido.
REGRAS = [
    {
        "nome": "dados_transacionais",
        "quando": lambda p: p["schema_fixo"] and p["precisa_acid"],
        "banco": "MySQL",
        "cap": "CP",
        "justificativa": (
            "O cenário exige transações ACID e possui estrutura de dados "
            "estável. O erro inaceitável seria confirmar uma operação "
            "parcialmente ou utilizar dados inconsistentes para autenticação "
            "ou controle de uma transação."
        ),
        "risco_owasp": "A07"
    },
    {
        "nome": "dados_distribuidos_disponiveis",
        "quando": lambda p: (
            p["escala_horizontal"]
            and p["tolera_atraso_de_consistencia"]
            and not p["precisa_acid"]
        ),
        "banco": "MongoDB",
        "cap": "AP",
        "justificativa": (
            "O cenário precisa suportar crescimento horizontal e aceita "
            "consistência eventual. O erro inaceitável seria deixar de "
            "receber dados durante um pico de utilização apenas para "
            "garantir consistência imediata."
        ),
        "risco_owasp": "A09"
    },
    {
        "nome": "auditoria_distribuida",
        "quando": lambda p: (
            p["escala_horizontal"]
            and not p["tolera_atraso_de_consistencia"]
        ),
        "banco": "MongoDB",
        "cap": "CP",
        "justificativa": (
            "O cenário precisa de escala horizontal, mas não pode aceitar "
            "divergência entre os registros. O erro inaceitável seria uma "
            "trilha de auditoria divergente ou incompleta ser utilizada "
            "como evidência confiável."
        ),
        "risco_owasp": "A08"
    },
]


def recomendar(perfil):
    """
    Analisa um perfil e retorna uma recomendação de armazenamento.

    Parâmetro:
        perfil (dict): características do conjunto de dados.

    Retorno:
        dict com banco, CAP, justificativa e risco OWASP.
    """

    campos_obrigatorios = {
        "schema_fixo",
        "precisa_acid",
        "escala_horizontal",
        "tolera_atraso_de_consistencia",
        "dado_sensivel",
    }

    campos_faltantes = campos_obrigatorios - perfil.keys()

    if campos_faltantes:
        raise ValueError(
            f"Perfil incompleto. Campos ausentes: {sorted(campos_faltantes)}"
        )

    for regra in REGRAS:
        if regra["quando"](perfil):
            return {
                "banco": regra["banco"],
                "cap": regra["cap"],
                "justificativa": regra["justificativa"],
                "risco_owasp": regra["risco_owasp"],
            }

    raise ValueError(
        "Não existe uma regra de decisão para o perfil informado."
    )


# Perfis fornecidos no enunciado
perfis = {
    "credenciais_do_SOC": {
        "schema_fixo": True,
        "precisa_acid": True,
        "escala_horizontal": False,
        "tolera_atraso_de_consistencia": False,
        "dado_sensivel": True,
    },

    "telemetria_de_sensores": {
        "schema_fixo": False,
        "precisa_acid": False,
        "escala_horizontal": True,
        "tolera_atraso_de_consistencia": True,
        "dado_sensivel": False,
    },

    "trilha_de_auditoria": {
        "schema_fixo": False,
        "precisa_acid": False,
        "escala_horizontal": True,
        "tolera_atraso_de_consistencia": False,
        "dado_sensivel": True,
    },

    "carrinho_de_licencas": {
        "schema_fixo": True,
        "precisa_acid": True,
        "escala_horizontal": False,
        "tolera_atraso_de_consistencia": False,
        "dado_sensivel": False,
    },

    "cache_de_sessoes": {
        "schema_fixo": True,
        "precisa_acid": False,
        "escala_horizontal": True,
        "tolera_atraso_de_consistencia": True,
        "dado_sensivel": True,
    },
}


# Resultados esperados conforme o enunciado
esperados = {
    "credenciais_do_SOC": {
        "banco": "MySQL",
        "cap": "CP",
        "risco_owasp": "A07",
    },

    "telemetria_de_sensores": {
        "banco": "MongoDB",
        "cap": "AP",
        "risco_owasp": "A09",
    },

    "trilha_de_auditoria": {
        "banco": "MongoDB",
        "cap": "CP",
        "risco_owasp": "A08",
    },

    "carrinho_de_licencas": {
        "banco": "MySQL",
        "cap": "CP",
        "risco_owasp": "A07",
    },

    "cache_de_sessoes": {
        "banco": "MongoDB",
        "cap": "AP",
        "risco_owasp": "A07",
    },
}

#Executa testes simples para validar os cinco cenários.
def testar_perfis():

    print("=" * 70)
    print("TESTE DO EXERCÍCIO 1")
    print("=" * 70)

    todos_passaram = True

    for nome, perfil in perfis.items():
        resultado = recomendar(perfil)
        esperado = esperados[nome]

        passou = (
            resultado["banco"] == esperado["banco"]
            and resultado["cap"] == esperado["cap"]
            and resultado["risco_owasp"] == esperado["risco_owasp"]
        )

        if passou:
            print(f"[OK] {nome}")
        else:
            todos_passaram = False
            print(f"[ERRO] {nome}")
            print(f"      Esperado: {esperado}")
            print(f"      Obtido:   {resultado}")

    print("=" * 70)

    if todos_passaram:
        print("[OK] Todos os perfis passaram nos testes.")
    else:
        print("[ERRO] Existem perfis com resultados incorretos.")


if __name__ == "__main__":
    testar_perfis()
