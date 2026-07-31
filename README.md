# Neural Link

A ponte física entre um dispositivo (Raspberry Pi, hoje; Orange Pi/Compute
Module/hardware próprio, amanhã) e a Neural Cloud.

```
Auriculares -> BLE -> Neural Link -> WebSocket -> neural_gateway
                                                 -> Cloud Runtime -> Core
```

**O Neural Link nunca executa Brain, Memory, Planning nem qualquer módulo
Cloud.** É só uma ponte inteligente: capta áudio, deteta a palavra-chave,
segmenta a frase, gere o dispositivo (bateria, ligação, fila offline), e
fala com a Cloud só por WebSocket/HTTP — protocolos públicos, nunca lógica
interna partilhada. Todo o raciocínio continua exclusivamente na Cloud.

## Instalar num dispositivo novo

```bash
git clone https://github.com/viape/neural-link.git
cd neural-link
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` instala o próprio `neural_link` em modo editável, com
o extra `[mic]` — que traz `neural-audio` (de `github.com/viape/
neural-audio`, repositório próprio, privado) já com suporte a microfone
(`sounddevice`). Necessário para `python -m neural_link.runtime.main`
funcionar independentemente do nome da pasta onde o repositório foi
clonado.

Os dois repositórios são **privados** — a máquina que faz o clone/
install precisa de credenciais Git configuradas (chave SSH ou token com
acesso a `viape/neural-link` e `viape/neural-audio`), tal como qualquer
outro `pip install` a partir de um repositório privado do GitHub.

Configurar (`config.toml`, ver `neural_link/runtime/configuration.py` para
todos os campos): `hostname`, `[gateway] host/port`, `tenant`, `device_id`.

Correr manualmente:
```bash
python -m neural_link.runtime.main --config /caminho/para/config.toml
```

Instalar como serviço residente (arranca no boot, reinicia sozinho):
```bash
python -c "from neural_link.runtime.service import install; \
  install(python_executable='$(which python3)', working_directory='$(pwd)')"
sudo systemctl daemon-reload
sudo systemctl enable --now neural-link
```

## Estrutura

```
neural_link/
    gateway/        WebSocketClient (standalone) + LinkGateway
    ble/             BLE — preparado, não implementado
    audio/             LinkAudioPipeline (mic -> wake word -> VAD -> encaminhar)
    devices/             DeviceManager + registo de placas (SimulatedBoard,
                         RaspberryPiBoard, ...)
    pairing/               preparado, não implementado
    security/                autenticação local Auriculares<->Link
    buffering/                 OfflineBuffer
    power/                       bateria do dispositivo
    updates/                       OTA — preparado, não implementado
    runtime/                         o serviço residente: máquina de
                                     estados, heartbeat, configuração,
                                     HAL, drivers, systemd
    tests/
```

## Dependências

`requirements.txt` — só `neural-audio` ([github.com/viape/neural-audio
](https://github.com/viape/neural-audio), repositório próprio: os
primitivos de voz partilhados com a Neural Cloud — `AudioChunk`, VAD,
wake word, captura de microfone). Tudo o resto é stdlib puro — zero
dependências de terceiros, mesma disciplina do resto da plataforma.

**Este repositório nunca precisa do monorepo principal (Neural Core) para
correr.** É a garantia verificada por `neural_link/runtime/tests/
test_di_boundaries.py`: zero imports de `neural_core` em qualquer
ficheiro deste pacote.

## Testar

```bash
pip install -r requirements.txt
pip install pytest
pytest runtime/tests \
  --ignore=runtime/tests/test_boot_sequence.py \
  --ignore=runtime/tests/test_connection_manager.py
```

Isto corre a suite de lógica do dispositivo (57 testes) só com
`neural_link` + `neural_audio` — nada mais.

`tests/` (o outro diretório de testes) **não corre fora do monorepo**:
`tests/conftest.py` importa `neural_runtime` ao nível do módulo para
alimentar uma única fixture usada por `tests/
test_end_to_end_link_to_cloud.py` (o teste de interoperabilidade real
com a Cloud) — e essa importação, por estar no `conftest.py`, impede o
pytest de sequer coligir os outros 12 ficheiros desse diretório, mesmo
que não precisem dela. Os dois ficheiros ignorados acima em `runtime/
tests/` têm a mesma natureza: usam `neural_gateway.transports.
WebSocketTransport` como servidor real para testar o cliente WebSocket
do Neural Link contra o protocolo, não porque o Neural Link dependa de
`neural_gateway` em produção (não depende — `neural_link/gateway/
ws_client.py` é uma implementação RFC6455 própria, do zero). Estes 3+1
ficheiros são testes de integração pensados para correr dentro do
monorepo, onde `neural_core`/`neural_runtime`/`neural_gateway` existem.
Isto também bloqueia `tests/test_di_boundaries.py` (o guarda de
arquitetura desse diretório) de correr isolado, por partilhar o mesmo
`conftest.py` — mas o seu equivalente, `runtime/tests/
test_di_boundaries.py`, corre normalmente no comando acima, e é ele que
prova a garantia de independência (zero import de `neural_core` em
`neural_link.runtime`).
