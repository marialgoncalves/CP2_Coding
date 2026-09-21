# Auditoria de Segurança — Exercício 10

1. **A03 — Injection:** a rota `/api/usuarios/buscar` concatenava diretamente a entrada do usuário na consulta SQL, permitindo SQL Injection. Correção: utilizar consultas parametrizadas com placeholders `%s`.

2. **A05 — Injection/XSS:** a rota `/perfil` retornava entrada controlada pelo usuário diretamente no HTML, permitindo XSS refletido. Correção: utilizar renderização Jinja2 com escape automático.

3. **A01 — Broken Access Control:** a rota DELETE não possuía autenticação nem autorização, permitindo que qualquer pessoa removesse usuários. Correção: exigir credencial e nível de acesso adequado.

4. **A05 — Security Misconfiguration:** o modo `debug=True` poderia expor informações internas da aplicação e traceback. Correção: executar a aplicação com `debug=False` e retornar mensagens genéricas ao cliente.

5. **A04 — Cryptographic Failures:** a resposta da busca utilizava `SELECT *`, podendo expor a coluna `senha`. Correção: selecionar somente os campos necessários e nunca retornar credenciais.

6. **A05 — Security Misconfiguration:** a aplicação não definia headers de segurança HTTP. Correção: adicionar `Content-Security-Policy`, `X-Content-Type-Options` e `X-Frame-Options`.

7. **A07 — Identification and Authentication Failures:** a API não possuía mecanismo de autenticação para proteger operações administrativas. Correção: validar uma credencial antes de permitir operações sensíveis.

8. **A02 — Cryptographic Failures:** a aplicação mantinha uma senha mestra diretamente no código-fonte (`SENHA_MESTRA`), expondo uma credencial caso o código fosse acessado. Correção: remover segredos do código e utilizar variáveis de ambiente ou um gerenciador de segredos.