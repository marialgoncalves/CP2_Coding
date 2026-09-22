# Exercício 1 — Assistente de decisão de armazenamento

REGRAS = [
    {
        "nome": "dados_transacionais",
        "quando": lambda p: (
            p["schema_fixo"]
            and p["precisa_acid"]
        ),
        "banco": "MySQL",
        "cap": "CP",
        "justificativa": (
            "O cenário possui estrutura estável e exige transações ACID. "
            "O erro inaceitável seria autenticar, registrar ou confirmar "
            "uma operação com dados inconsistentes ou parcialmente gravados."
        ),
        "risco_owasp": "A07"
    },
    {
        "nome": "cache_de_sessoes_sensivel",
        "quando": lambda p: (
            p["schema_fixo"]
            and p["escala_horizontal"]
            and p["tolera_atraso_de_consistencia"]
            and p["dado_sensivel"]
            and not p["precisa_acid"]
        ),
        "banco": "MongoDB",
        "cap": "AP",
        "justificativa": (
            "O cache de sessões precisa escalar horizontalmente e pode "
            "tolerar atraso de consistência, mas contém dados sensíveis "
            "relacionados à sessão. O erro inaceitável seria uma falha de "
            "autenticação ou perda de disponibilidade causada pela tentativa "
            "de exigir consistência imediata em todo o cache."
        ),
        "risco_owasp": "A07"
    },
    {
        "nome": "dados_distribuidos_disponiveis",
        "quando": lambda p: (
            p["escala_horizontal"]
            and p["tolera_atraso_de_consistencia"]
            and not p["precisa_acid"]
            and not p["dado_sensivel"]
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
            f"Perfil incompleto. Campos ausentes: "
            f"{sorted(campos_faltantes)}"
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