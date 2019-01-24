# zapzap_exporter

Exportação interativa das conversas de WhatsApp através da UiAutomator do Android

## Pré-requisitos

### Ambiente

1. [Python 3](https://www.python.org/)
2. [Android SDK tools](https://developer.android.com/studio/) com a variável `ANDROID_HOME` configurada.
3. `python -m pip install -U requests`

### Smartphone

Habilitar modo desenvolvedor,

1. Depuração USB
2. Manter sempre ativo
3. Não verificar apps instalados por ADB
4. Permitir instalação de app de fontes desconhecidas
 
## Utilização

```
usage: python zapzap_exporter.py [-h] [--install | --uninstall | --info] [--debug]

Exporta interativamente as conversas do WhatsApp 

optional arguments: 
-h, --help   show this help message and exit
--install    Somente instala os aplicativos necessários
--uninstall  Somente remove os aplicativos que foram instalados
--info       Somente imprime informações do dispositivo
--debug      Ativa mensagens de debug no log de arquivo
```

## Tools

Na pasta `tools` há o script `unzip_conversations.py` que, passado o diretório como argumento, remove todos os arquivos com (1), (2), etc. no nome, e unzipa todas as conversas `.zip`