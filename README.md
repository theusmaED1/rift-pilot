# Rift Pilot

Seu coach de voz em português para **League of Legends**. Lê em voz alta a build recomendada, lembretes de skill, spawns dos objetivos neutros, lembretes do minimapa e quando você acumula ouro suficiente para o próximo item — tudo em tempo real, durante a partida.

Funciona usando apenas a **Live Client Data API oficial** da Riot (endpoint local `127.0.0.1:2999`), sem injeção de código, leitura de memória ou modificação do cliente. Portanto, é **permitido pelos Termos de Serviço** da Riot.

---

## Como instalar

1. Baixe o instalador `RiftPilot-Setup-X.Y.Z.exe` na aba **Releases** do repositório.
2. Execute o instalador. Ele cria um atalho no Menu Iniciar (e na área de trabalho, se você marcar a opção).
3. Pronto — pode abrir o **Rift Pilot** antes ou depois de entrar em partida.

> Requisitos: **Windows 10 ou 11**, League of Legends instalado e conexão com internet (a síntese de voz usa o Microsoft Edge TTS).

---

## Como usar

1. Entre numa partida de LoL (qualquer modo: normal, ranqueada, ARAM).
2. Abra o **Rift Pilot**.
3. Clique em **▶ INICIAR**.

Quando o app detectar o jogo, carrega automaticamente a build recomendada para o seu campeão na sua lane (extraída do deeplol.gg, tier Emerald+) e começa a anunciar. A janela exibe a build completa em tempo real e mostra um log com tudo que foi anunciado.

Para parar, clique em **■ PARAR**.

---

## Features

Cada feature pode ser ligada/desligada individualmente nos switches da seção **AVISOS ATIVOS**.

### ✦ Pontos de skill disponíveis
Avisa toda vez que você sobe de nível e tem skill para evoluir. Quando a build do deeplol traz a sequência exata por nível, o coach recomenda **qual** skill (Q / W / E / R) upar; caso contrário, usa uma tabela bundled com a ordem de maximização dos campeões mais populares.

Se você demorar a gastar o ponto, repete o lembrete a cada poucos segundos. Assim que o ponto for gasto, os lembretes pendentes são automaticamente cancelados.

### ♛ Objetivos (Dragão, Barão, Arauto, Larvas)
Anuncia o **spawn inicial** e cada **respawn** de dragão, barão e arauto — sempre 1 minuto, 30 segundos e 10 segundos antes. O detector escuta os eventos `DragonKill`, `BaronKill` e `HeraldKill` da Live API para recalcular o timer quando o objetivo morre.

### ► Anunciar build no início da partida
Logo após a build ser carregada, faz uma fala única lendo: campeão e lane, itens iniciais, itens core na ordem, botas e ordem de maximização das skills.

### ● Lembrete do próximo item da build
A cada 2 minutos, fala qual é o **próximo item** a comprar (pulando os que você já tem). Independente do timer, **assim que o ouro cruza o preço** do próximo item, dispara um aviso imediato com prioridade maior que o lembrete periódico.

### ◎ Lembrete do minimapa
Avisa periodicamente (a cada 45–90 segundos, intervalo variado) para você checar o minimapa, com frases curtas e imperativas.

---

## Privacidade e termos de uso

- O app **não modifica** nada do cliente do LoL — apenas lê o endpoint público local `127.0.0.1:2999/liveclientdata`, exposto oficialmente pela Riot para integrações de terceiros.
- A busca de build é feita no [deeplol.gg](https://deeplol.gg) (público, sem autenticação).
- A síntese de voz é feita pelo serviço **Microsoft Edge TTS**. O texto da fala é enviado ao serviço da Microsoft para gerar o áudio.
- Nenhum dado pessoal é coletado ou armazenado pelo app.

---

## Compilando do código-fonte

Pré-requisitos:
- **Python 3.11+**
- **[Inno Setup 6](https://jrsoftware.org/isdl.php)** (para gerar o instalador)

```powershell
git clone https://github.com/<seu-usuario>/rift-pilot.git
cd rift-pilot

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Gera o .exe e o instalador
.\scripts\build_installer.ps1
```

Saída:
- `dist\rift-pilot.exe` — executável standalone
- `dist\installer\RiftPilot-Setup-0.1.0-beta.exe` — instalador final

---

## Para desenvolvedores

### Estrutura de pastas

```
src/rift_pilot/
├── settings/          # Constantes, mensagens pt-BR, loader de config
├── domain/            # Regras puras: entidades + detectores + ports (Protocols)
├── application/       # Casos de uso: CoachSession, BuildLoader
├── infrastructure/    # I/O: Live API, deeplol, Data Dragon, Edge TTS
└── presentation/      # GUI (Tkinter) e CLI (replay)
```

A camada **domain** não conhece nenhuma outra. **infrastructure** implementa os Protocols definidos em `domain/ports/`. **application** orquestra usando injeção pelo construtor. **presentation** é a única que monta o grafo de dependências.

### Rodando os testes

```powershell
pytest
```

Os testes cobrem só o domínio (sem mocks de I/O) — detectores e diffs de estado sobre estados fabricados.

### Modo CLI: rodar contra um replay gravado

```powershell
# Grava uma partida ao vivo para .jsonl
python scripts\log_game.py

# Reproduz o replay como se fosse uma partida real (anuncia tudo)
python -m rift_pilot.presentation.cli.cli_runner --replay caminho\do\replay.jsonl
```

---

## Licença

MIT.
