# Auditoria de Segurança — Exercício 10

1. **A05 — Injection:** a rota `/api/usuarios/buscar` concatenava diretamente a entrada do usuário na consulta SQL, permitindo SQL Injection e vazamento de registros. Correção: utilizar consultas SQL parametrizadas com placeholders `%s`.

2. **A05 — Injection:** a rota `/perfil` inseria diretamente entrada controlada pelo usuário no HTML, permitindo XSS refletido. Correção: utilizar renderização com Jinja2 e escape automático dos valores.

3. **A01 — Broken Access Control:** a rota DELETE não possuía autenticação nem autorização, permitindo que qualquer usuário removesse registros. Correção: exigir autenticação e verificar o nível de autorização antes da operação.

4. **A10 — Mishandling of Exceptional Conditions:** a aplicação executava com `debug=True`, podendo expor traceback e informações internas quando ocorria uma exceção. Correção: desabilitar o modo debug em produção e retornar uma mensagem genérica de erro ao cliente.

5. **A01 — Broken Access Control:** a consulta utilizava `SELECT *` e podia retornar a coluna `senha`, expondo informação sensível pela API. Correção: selecionar somente as colunas necessárias e nunca retornar credenciais na resposta.

6. **A02 — Security Misconfiguration:** a aplicação não configurava headers HTTP de segurança. Correção: adicionar `Content-Security-Policy`, `X-Content-Type-Options` e `X-Frame-Options`.

7. **A07 — Authentication Failures:** a API não possuía mecanismo de autenticação para proteger operações administrativas. Correção: validar uma credencial antes de permitir operações sensíveis.

8. **A04 — Cryptographic Failures:** a aplicação possuía um segredo sensível (`SENHA_MESTRA`) diretamente no código-fonte. Correção: remover o segredo do código e utilizar variáveis de ambiente ou um gerenciador de segredos.