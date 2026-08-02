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
os extras `[mic,wake]` — que trazem `neural-audio` (de `github.com/viape/
neural-audio`, repositório próprio, privado) já com suporte a microfone
(`sounddevice`) e a deteção de wake word real (`openwakeword`).
Necessário para `python -m neural_link.runtime.main` funcionar
independentemente do nome da pasta onde o repositório foi clonado.

Os dois repositórios são **privados** — a máquina que faz o clone/
install precisa de credenciais Git configuradas (chave SSH ou token com
acesso a `viape/neural-link` e `viape/neural-audio`), tal como qualquer
outro `pip install` a partir de um repositório privado do GitHub.

`openwakeword` precisa dos modelos ONNX descarregados uma vez (não vêm
no pacote):
```bash
python3 -c "import openwakeword.utils as u; u.download_models(model_names=['hey_jarvis'])"
```
Sem isto (ou sem `[wake]` instalado), o dispositivo arranca à mesma —
cai no `NullWakeWordProvider` (nunca ouve, mas nunca crasha) e regista
um aviso claro no log. Só modelos em inglês existem pré-treinados
(`hey_jarvis`, `alexa`, `hey_mycroft`, ...); sem modelo português, é a
limitação honesta desta v1.

Configurar (`config.toml`, ver `neural_link/runtime/configuration.py` para
todos os campos): `hostname`, `[gateway] host/port`, `tenant`, `device_id`,
`[wake_word] model/threshold` (omissão: `"hey_jarvis"` / `0.5`).

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

## Auriculares Bluetooth (A2DP)

O emparelhamento em si é um passo do SO (`bluetoothctl`), fora deste
código — mas numa instalação nova, `bluetoothctl connect` falha quase
sempre com `br-connection-profile-unavailable`, por duas razões que não
têm nada a ver com o dispositivo Bluetooth em si:

**1. O WirePlumber nunca liga o Bluetooth numa sessão sem ecrã.**
`monitors/bluez.lua` só cria o monitor Bluetooth quando o *seat* da
sessão está `"active"` (sessão gráfica/consola em primeiro plano) — uma
sessão `systemd --user` criada por SSH fica para sempre em `"online"`,
nunca `"active"`, e o script fica parado à espera, em silêncio, sem
nenhum erro nos logs. `wpctl status` nunca mostra nada em "Bluetooth", e
`bluetoothctl show` nunca lista os UUIDs de A2DP no adaptador. Corrigir
com um override local (não mexe no `main-embedded`, que também desliga
o *state.restore* do pairing — não queremos perder isso):

```bash
mkdir -p ~/.config/wireplumber/wireplumber.conf.d
cat > ~/.config/wireplumber/wireplumber.conf.d/99-bluez-sem-seat.conf << 'EOF'
wireplumber.profiles = {
  main = {
    monitor.bluez.seat-monitoring = disabled
  }
}
EOF
systemctl --user restart wireplumber
```

Confirmar que resolveu: `bluetoothctl show | grep -i uuid` deve passar
a listar `Audio Source (0000110a)` e `Audio Sink (0000110b)`.

**2. `sounddevice`/PortAudio nunca chega ao PipeWire sem `pipewire-alsa`.**
Sem este pacote, o dispositivo ALSA `default` (o que `SpeakerPlayback`/
`RaspberryPiSpeakerDriver` usam por omissão) vai direto ao hardware de
áudio físico do Pi — mesmo com os auriculares já ligados como sink por
omissão do PipeWire, nada sai por eles, porque o código nunca fala com
o PipeWire.

```bash
sudo apt install pipewire-alsa
```

Confirmar: `python3 -c "import sounddevice as sd; print(sd.query_devices())"`
deve listar um dispositivo `pipewire` com dezenas de canais (`64 in, 64
out`, tipicamente) — se só aparecerem `bcm2835 Headphones`/`sysdefault`/
`dmix`, o plugin ainda não está a ser usado.

Só depois destes dois passos é que `bluetoothctl pair`/`trust`/`connect`
tem alguma hipótese de funcionar. Se mesmo assim `connect` devolver
`br-connection-refused` (diferente de `br-connection-profile-unavailable`
— já é sinal de que o perfil A2DP existe), o problema passou a ser o
pairing em si, não a configuração: `bluetoothctl remove <MAC>` seguido de
`pair`/`trust`/`connect` outra vez, com os auriculares em modo de
emparelhamento, normalmente resolve.

Nenhum destes dois passos faz parte deste repositório nem do
`requirements.txt` — são configuração do sistema operativo do Pi, por
isso um `git pull` nunca os traz de volta. Precisam de ser repetidos em
qualquer dispositivo novo.

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
