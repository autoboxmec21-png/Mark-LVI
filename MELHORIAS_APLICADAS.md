# Mark-LVI — melhorias incluídas nesta versão

Este pacote reúne as correções de estabilidade/segurança que já havíamos preparado
para o projeto e as três otimizações de desempenho solicitadas depois.

## Correções anteriores preservadas

1. **Limite de chamadas de ferramentas (pipeline local):** chamadas repetidas com
   os mesmos argumentos reutilizam o resultado anterior, sem executar a ação de
   novo. A cadeia é limitada a quatro rodadas; ao atingir o limite, o modelo
   recebe instrução para responder sem ferramentas, e chamadas extras são ignoradas.
2. **Dashboard remoto:** HTTPS passa a ser o padrão. Se a criação do certificado
   falhar, o dashboard não inicia em HTTP por fallback silencioso. HTTP só fica
   disponível quando `dashboard_https` é explicitamente `false` em
   `config/api_keys.json`.
3. **Configuração concorrente:** as gravações são serializadas por lock e feitas
   por arquivo temporário seguido de substituição atômica, evitando JSON parcial
   e atualizações simultâneas perdidas.
4. **Diagnóstico do Ollama:** a saída de `ollama serve` é gravada em
   `logs/ollama.log`, em vez de ser descartada.

## Três otimizações de desempenho solicitadas

1. **Avatar (`core/avatar.py`):** preenchimentos dos triângulos da malha são
   agrupados em caminhos de pintura por camada e tonalidade, reduzindo chamadas
   individuais ao QPainter. A ordem entre pescoço e cabeça é mantida.
2. **Sincronização labial (`main.py`):** janela Hann e máscaras de frequência da
   FFT são pré-calculadas e reutilizadas por taxa de amostragem, evitando recriá-las
   a cada bloco de áudio.
3. **HTTP persistente (`core/llm_client.py`):** sessões `requests.Session` com
   pool de conexões reutilizadas por thread, permitindo keep-alive sem compartilhar
   uma sessão mutável entre threads.

## Validação realizada neste ambiente

- `compileall` em todo o projeto: passou.
- Teste direcionado da cache FFT: passou.
- Teste direcionado de sessões HTTP por thread: passou.
- Teste concorrente de 30 atualizações de configuração: passou, sem perder entradas.
- Teste direcionado do limite de ferramentas: passou; uma ação foi despachada uma
  única vez, repetições reutilizaram o resultado e a geração terminou sem ferramentas.
- Teste da política HTTPS: padrão seguro, opt-out explícito e configuração inválida
  verificados.
- Teste do log do Ollama com processo simulado: passou.

**Limitações:** `python -m providers._tests` não pôde completar porque o ambiente
não tem `google.genai` instalado. O ambiente também não tem PyQt6, então não foi
possível abrir a interface e fazer validação visual/medição de FPS do avatar.
Não afirmamos benchmark nem ganho numérico de desempenho; esses devem ser medidos
na máquina onde o MARK LVI será executado.

## Observação sobre HTTPS

A primeira conexão ao dashboard HTTPS pode pedir que o certificado local
autoassinado seja aceito no telefone. Para desativar HTTPS deliberadamente em
uma rede confiável, defina `"dashboard_https": false` no arquivo
`config/api_keys.json`.


## Redesign visual — Cyber / Holo / Immersive

- **Interface Cyber:** paleta ultravioletas, superfícies grafite-violeta e acentos
  ciano/magenta, mantendo as cores semânticas de estado (escuta, fala, erro).
- **Layout imersivo:** janela inicial maior e centralizada conforme a resolução;
  laterais compactadas para liberar espaço ao avatar sem remover painéis, comandos,
  upload, monitoramento, logs ou controles.
- **Avatar Holo (referência de partículas):** o centro visual foi redesenhado como
  um volume orgânico de pontos luminosos, com gradientes azul/ciano e violeta,
  deformação fluida e brilho que reage ao nível de áudio e ao estado do assistente.
  O ciclo de atualização e a entrada de áudio continuam ligados ao mesmo HoloAvatar;
  como o rosto foi substituído por uma forma abstrata, não há boca visível para
  representar fonemas, embora o pipeline de visemas e fala permaneça preservado.
- **Compatibilidade:** o layout continua redimensionável e não força fullscreen.
  A opção de estilo de HUD e a personalização de cor continuam disponíveis.

O ambiente de execução usado para empacotar não possui PyQt6; portanto, a interface
precisa de validação visual na máquina de destino. Nenhum benchmark de FPS foi
realizado nesta etapa.

## Atualização baseada na primeira referência enviada

- `core/avatar.py`: substituído o desenho facial no modo principal por uma esfera
  orgânica de partículas animadas, com cerca de 1.900 pontos por quadro, brilho
  azul/ciano e bordas violetas. O movimento acompanha o relógio interno e a
  intensidade de áudio já fornecida pelo pipeline.
- Não foram adicionadas dependências externas nem removidas as rotinas anteriores
  de geometria facial; elas permanecem no código para permitir uma futura opção de
  alternância entre rosto e campo de partículas.
- `compileall` passou após a alteração. PyQt6 não está instalado neste ambiente,
  então a renderização real e o FPS ainda precisam ser verificados no computador
  de destino.
