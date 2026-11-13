# Inventário de limpeza · 13 de novembro de 2026

Medição local da árvore de trabalho antes da reorganização, em MiB. Os volumes variam após builds, coletas e reinstalações. Nenhum dos itens inventariados foi excluído nesta revisão.

| Item | Volume observado | Recomendação e efeito |
|---|---:|---|
| `venv/` | 270,3 MiB · 7.072 arquivos | Prioridade para retirar do índice Git em uma mudança dedicada. Existem **4.233 arquivos rastreados** e o executável aponta para uma instalação Python ausente. Recriar em `.venv/`, instalar os requisitos e validar a CLI antes de descartar a cópia. A regra de ignore adicionada só protege arquivos ainda não rastreados. A retirada do índice mantém a cópia local e o histórico Git. |
| `frontend/node_modules/` | 82,8 MiB · 7.038 arquivos | Reinstalável com `npm ci`. Remover com o servidor parado. Preservar os dois manifestos npm, inclusive o lockfile. |
| `frontend/dist/` | 1,1 MiB · 8 arquivos | Recriável com `npm run build`. Preservar se alguma implantação estiver servindo essa pasta. |
| `__pycache__/` e caches dentro dos pacotes | 0,3 MiB na raiz | Bytecode regenerado pelo Python. Pode ser limpo com o interpretador parado. |
| `tests/__pycache__/` | 3 arquivos · < 0,1 MiB | Restos compilados. A pasta não contém fontes de testes nesta revisão. As fontes anteriores estão no commit `250ddfc`; revisar sua compatibilidade antes de recuperar a suíte. |
| `frontend/public/` | Vazia | Removível enquanto não houver recursos estáticos independentes. |
| `perfil_navegador/` | 583,6 MiB · 4.498 arquivos | **Preservar.** O coletor reutiliza login e cookies. Descartar apenas se o operador quiser reiniciar as sessões com o navegador fechado. |
| `Planilhas/` | 1,4 MiB · 3 arquivos | **Preservar.** Dois PDFs e um JSON. Arquivar PDFs individualmente se necessário. Remover o histórico pode reintroduzir empresas em coletas futuras. |
| `.gemini/settings.json`, `.skills.json` | Configuração | Revisar se o time abandonar essas ferramentas. A preferência por outro visual não é suficiente para concluir que essas configurações perderam a função. |
| `.vscode/settings.json` | Configuração | Manter a configuração compartilhada do interpretador apontando para o ambiente recomendado no README. |
| `.impeccable/`, `DESIGN.md`, `PRODUCT.md` | Diretrizes | Manter. Alimentam o trabalho de produto e design. |
| `.git/`, fontes, requisitos e documentação | Histórico e entregáveis | Manter. O DOCX oficial precisa ser versionável; arquivos temporários do Word continuam ignorados. |

As três pastas reinstaláveis de maior interesse somam cerca de **354,2 MiB**. A economia em disco dura até a próxima instalação ou compilação. Para reduzir a poluição do repositório, a maior diferença vem de deixar de rastrear o ambiente Python. O tamanho da árvore de trabalho não mede a redução do histórico Git.
