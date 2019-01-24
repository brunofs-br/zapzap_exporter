# coding: utf-8

# Programas e arquivos necessários para o uiautomator funcionar com o smartphone
# 
# `
# adb shell pm uninstall com.github.uiautomator
# adb shell pm uninstall com.github.uiautomator.test
# 
# adb install -r -t uiautomator/libs/app-uiautomator.apk
# adb install -r -t uiautomator/libs/app-uiautomator-test.apk
# 
# adb push bundle.jar /data/local/tmp/
# adb push uiautomator-stub.jar /data/local/tmp/
# `

from uiautomator import device as DEVICE
from uiautomator import JsonRPCError
import xml.etree.ElementTree
from enum import Enum
import logging
import time
import sys
import os
from collections import OrderedDict
from itertools import islice
from functools import partial
import argparse

"""Log"""
__logging_level = logging.INFO
logger = logging.getLogger('zapzap_exporter')
logger.setLevel(__logging_level)

logf = logging.FileHandler('zapzap_exporter.log', encoding="UTF-8")
logc = logging.StreamHandler(sys.stdout)
logc.setLevel(logging.INFO)

logformat = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
logf.setFormatter(logformat)

logger.addHandler(logf)
logger.addHandler(logc)

"""__apks -- Mapeamento do arquivo .apk com o nome do pacote"""
__apks = {
    # 'apps/EmailBkpToFile_Android5_above.apk': 'br.gov.pr.policiacientifica.computacao.emailbkptofile',
    'apps/app-debug.apk': 'br.gov.pr.policiacientifica.computacao.emailbkptofile',
    'uiautomator/libs/app-uiautomator.apk': 'com.github.uiautomator',
    'uiautomator/libs/app-uiautomator-test.apk': 'com.github.uiautomator.test'
}


class ResolverType(Enum):
    LIST = 0
    PAGE = 1
    NOTDEFINED = 99


class Screen(Enum):
    CHAT_LIST = 0
    CHAT = 1
    CHAT_OPTION = 2
    CHAT_OPTION_PLUS = 3
    CHAT_INCLUDE_MEDIA = 4
    CHAT_SEND_BY_MATCH_APP = 5  # Tela de escolha de aplicativos com o "Email Bkp.." aparecendo
    CHAT_SEND_BY = 6  # Tela de escolha de aplicativos
    PERMISSION_MANAGER = 7
    FILECHOOSER_SELECT = 8  # Tela com o diretório já selecionado
    FILECHOOSER_OPEN_FROM = 9  # Abrir de:
    FILECHOOSER = 10  # Tela de "Recentes"
    FILECHOOSER_GENERIC = 11  # Identifica o pacote
    EMAILBKP_ERRORDIR = 12  # Diretório não escolhido
    EMAILBKP_OK = 13
    MODAL_INICIALIZANDO = 50
    ERROR_CANNOT_EXPORT = 60
    TEST = 98
    NONE = 99


"""SCREEN_XPATH_SEARCH_ID
Dicionário que interliga a tela com o XPath que a identifica"""
SCREEN_XPATH_SEARCH_ID = {
    Screen.CHAT_LIST: './/*[@resource-id="com.whatsapp:id/conversations_row_contact_name"]',
    Screen.CHAT: './/*[@resource-id="com.whatsapp:id/conversation_contact"]',
    Screen.CHAT_OPTION: './/*[@class="android.widget.TextView"][@text="Mais"]',
    Screen.CHAT_OPTION_PLUS: ('.//*[@text="Exportar conversa"]',
                              './/*[@text="Enviar por email"]'),
    Screen.CHAT_INCLUDE_MEDIA: ('.//*[@class="android.widget.Button"][@text="INCLUIR ARQUIVOS DE MÍDIA"]',
                                './/*[@class="android.widget.Button"][@text="Incluir arquivos de mídia"]'),
    # Screen.CHAT_SEND_BY_MATCH_APP: './/*[@resource-id="android:id/resolver_list"]//*[@text="Email Bkp Para Arquivo"]',
    Screen.CHAT_SEND_BY_MATCH_APP: './/*[@resource-id="android:id/contentPanel"]//*[@text="Email Bkp Para Arquivo"]',
    # Screen.CHAT_SEND_BY: './/*[@class="android.widget.ScrollView"]/*[@resource-id="android:id/resolver_list"]',
    Screen.CHAT_SEND_BY: './/*[@resource-id="android:id/contentPanel"][@class="android.widget.ScrollView"]',
    Screen.PERMISSION_MANAGER: './/*[@class="android.widget.Button"][@resource-id="com.android.packageinstaller:id/permission_allow_button"]',
    # Screen.FILECHOOSER_SELECT: './/*[@resource-id="android:id/button1"][@text="SELECIONAR"]',
    Screen.FILECHOOSER_SELECT: './/*[@resource-id="android:id/button1"][@package="com.android.documentsui"]',
    Screen.FILECHOOSER_OPEN_FROM: './/*[@resource-id="com.android.documentsui:id/drawer_roots"]',
    Screen.FILECHOOSER: './/*[@content-desc="Mostrar raízes"]/..*[@text="Recentes"]',
    # OBS. Inclui demais FILECHOOSER excluindo o SELECT
    Screen.FILECHOOSER_GENERIC: './/*[@package="com.android.documentsui"]',  # OBS. Inclui todos os FILECHOOSER_*
    Screen.EMAILBKP_ERRORDIR: './/*[@text="ERRO: diretório de saída não configurado!"]',
    Screen.EMAILBKP_OK: './/*[@resource-id="br.gov.pr.policiacientifica.computacao.emailbkptofile:id/btnClose"]',
    # OBS. Inclui EMAILBKP_ERRORDIR
    Screen.MODAL_INICIALIZANDO: './/*[@resource-id="android:id/alertTitle"][@text="Inicializando…"]',
    Screen.ERROR_CANNOT_EXPORT: './/*[@resource-id="android:id/message"][@text="Não foi possível exportar a conversa."]',
    Screen.TEST: './/*[@resource-id="android:id/resolver_list"]',
    Screen.NONE: '',
    ResolverType.LIST: './/*[@resource-id="android:id/resolver_list"]',
    ResolverType.PAGE: './/*[@resource-id="android:id/resolver_page"]',
}

"""SCREEN_SELECTOR_ID
Dicionário que identifica a tela com um UiSelector
Segue o padrão do XPath mas para ser utilizado por ex. com as condições no UiAutomator"""
SCREEN_SELECTOR_ID = {
    Screen.CHAT_LIST: {'resourceId': 'com.whatsapp:id/conversations_row_contact_name'},
    Screen.CHAT: {'resourceId': 'com.whatsapp:id/conversation_contact'},
    # ...
    Screen.CHAT_INCLUDE_MEDIA: {'textContains': 'mídia', 'resourceId': 'android:id/message'},
    Screen.CHAT_SEND_BY_MATCH_APP: {'text': 'Email Bkp Para Arquivo', 'className': 'android.widget.TextView'},
    # Screen.CHAT_SEND_BY: {'resourceId':'android:id/resolver_list'},
    Screen.CHAT_SEND_BY: {'resourceId': 'android:id/contentPanel', 'className': 'android.widget.ScrollView'},
    # ...
    Screen.FILECHOOSER_GENERIC: {'packageName': 'com.android.documentsui'},
    # ...
    Screen.NONE: {},
}

"""SCREEN_NEXT_SELECTOR
Dicionário que interliga a tela atual com o elemento gráfico 
que deve ser encontrado para próxima ação."""
SCREEN_NEXT_SELECTOR = {
    Screen.CHAT_LIST: {'resourceId': 'com.whatsapp:id/conversations_row_contact_name'},
    Screen.CHAT: {'description': 'Mais opções'},
    Screen.CHAT_OPTION: {'text': 'Mais', 'resourceId': 'com.whatsapp:id/title'},
    Screen.CHAT_OPTION_PLUS: ({'text': 'Exportar conversa', 'className': 'android.widget.TextView'},
                              {'text': 'Enviar por email', 'className': 'android.widget.TextView'}),
    Screen.CHAT_INCLUDE_MEDIA: {'resourceId': 'android:id/button1', 'className': 'android.widget.Button'},
    Screen.CHAT_SEND_BY_MATCH_APP: {'text': 'Email Bkp Para Arquivo', 'className': 'android.widget.TextView'},
    Screen.CHAT_SEND_BY: {'resourceId': 'android:id/contentPanel', 'className': 'android.widget.ScrollView'},
    # Fazer scroll até encontrar a tela CHAT_SEND_BY_MATCH_APP
    Screen.PERMISSION_MANAGER: {'resourceId': 'com.android.packageinstaller:id/permission_allow_button'},
    # Screen.FILECHOOSER_SELECT: {'text':'SELECIONAR', 'resourceId':'android:id/button1'},
    Screen.FILECHOOSER_SELECT: {'packageName': 'com.android.documentsui', 'resourceId': 'android:id/button1'},
    Screen.FILECHOOSER_OPEN_FROM: {},  # TODO: Definir como clicar no cartão SD
    Screen.FILECHOOSER: {'description': 'Mostrar raízes'},
    Screen.EMAILBKP_ERRORDIR: {'text': 'escolher diretório...', 'className': 'android.widget.Button'},
    Screen.EMAILBKP_OK: {'resourceId': 'br.gov.pr.policiacientifica.computacao.emailbkptofile:id/btnClose'},
    Screen.MODAL_INICIALIZANDO: {'resourceId': 'android:id/alertTitle', 'text': 'Inicializando…'},
    Screen.ERROR_CANNOT_EXPORT: {'text': 'OK'},
    Screen.NONE: {},
    ResolverType.LIST: {'resourceId': 'android:id/resolver_list'},
    ResolverType.PAGE: {'resourceId': 'android:id/resolver_page'},
}


class ExportException(Exception):
    """Exceção para tratar erros do script"""
    pass


os.environ['JSONRPC_TIMEOUT'] = '50'

NEUTRAL_POS = (200, 100)  # TODO: Pegar valor relativo à resolução do aparelho
APP_SCROLL_RESOLVER = ResolverType.NOTDEFINED  # android:id/resolver_list | android:id/resolver_page


def screen_dump():
    """Realiza um 'dump' da tela atual e retorna como ElementTree"""

    logger.debug('Despejando tela do dispositivo')
    dump = DEVICE.dump()
    return xml.etree.ElementTree.fromstring(dump)


def wait_screen(screen_type, timeout=3000):
    """Usa o seletor da tela para aguardar sua identificação
    Retorna o sucesso na operação"""

    logger.debug(f'Aguardando tela {screen_type.name} por até {timeout} ms')
    ret = DEVICE(**SCREEN_SELECTOR_ID[screen_type]).wait.exists(timeout=timeout)
    return ret


def is_from_screen(xml_element: xml.etree.ElementTree, screen_type: Screen) -> tuple:
    """Verifica se a tela descrita no 'xml' é a informada em screen_type
    xml_element -- ElementTree's Element
    screen_type -- Screen(Enum)
    retorna tupla (index, bool) com o índice do xpath verificado e se foi encontrada a tela ou não
    """

    logger.debug(f'Verificando tela: {screen_type.name}')
    search_str = SCREEN_XPATH_SEARCH_ID[screen_type]
    if not isinstance(search_str, tuple):
        search_str = (search_str, )

    return next((x for x in enumerate(search_str) if xml_element.findall(x[1])), (0, False))
    # return any(map(xml_element.findall, search_str))


def detect_screen(xml_element: xml.etree.ElementTree) -> tuple:
    """Descobre qual é a tela descrita pelo xml do 'dump'
    xml_string -- saída de DEVICE.dump()
    retorna tupla (índice, tela)"""

    logger.debug(f'Detectando tela...')
    for screen in SCREEN_XPATH_SEARCH_ID.keys():
        index, found = is_from_screen(xml_element, screen)
        if found:
            logger.debug(f'Tela encontrada: {screen.name}')
            return index, screen
    else:
        logger.debug('Tela não detectada')
        return 0, Screen.NONE


def find_element(params):
    """Encontra o elemento na tela
    params -- dict com os parâmetros que vão ser passados por kwargs
    ex: {text : 'Mais', resourceId : 'com.whatsapp:id/title'}"""

    logger.debug(f'Procurando elemento: {params}')
    element = DEVICE(**params)
    if __logging_level == logging.DEBUG:
        if len(element) > 1:
            logger.debug(f'Elementos encontrados total: {len(element)}')
        elif element:
            logger.debug(f'Elemento encontrado: {element.info}')
        else:
            logger.debug(f'Elemento não encontrado')
    return element


def install_apk(filename):
    """Instala .apk
    Ex.: filename='apps/app-debug.apk' """
    logger.info(f'Instalando APK: {filename}')
    return DEVICE.server.adb.cmd('install', '-r', '-t', filename).wait()


def remove_apk(package_name):
    logger.info(f'Removendo do dispositivo: {package_name}')
    return DEVICE.server.adb.cmd('shell', 'pm', 'uninstall', package_name).wait()


def clean_up():
    """Remove todos os APKs de perícia"""
    for apkfile, package in __apks.items():
        remove_apk(package)


def back_to_chat_list():
    element = {'resourceId': 'com.whatsapp:id/back'}
    element_obj = find_element(element)
    logger.info('Retornando à lista de conversas')
    return element_obj.click.wait()


def get_chat_list():
    """A partir da tela com a lista de conversas, retorna os elementos com os nomes."""
    logger.debug('Extraindo lista de conversas')
    return find_element(SCREEN_NEXT_SELECTOR[Screen.CHAT_LIST])


def scroll_chat_list(conversation_elements, scrolling_size=0.5):
    """A partir da tela com a lista de conversas, realiza um 'scroll' para cima.
    conversation_elements -- Retorno de Selector 'find_element' para a SCREEN_NEXT_SELECTOR[Screen.CHAT_LIST]
    scrolling_size -- Quantidade de tela que deverá ser feito scroll
    Retorna a tela atualizada, após o scroll, selecionada pelo Selector"""

    if scrolling_size <= 0 or scrolling_size > 1:
        logger.debug('Não é possível realizar "scroll" da tela com o parâmetro passado. Utilizando valor padrão 0.5')
        scrolling_size = 0.5

    c_len = len(conversation_elements)
    c_pickscroll = int(c_len * scrolling_size)
    c1 = conversation_elements[0].info['bounds']
    c2 = conversation_elements[c_pickscroll].info['bounds']

    tsteps = round(c_pickscroll * 10)  # 10 steps por mensagem

    pixels = c2['top'] - c1['top']
    ret = DEVICE.drag(c2['left'], c2['top'], c1['left'], c1['top'], steps=tsteps)
    if ret:
        logger.debug(f'[SCROLL] {pixels} pixels, em {tsteps} passos')
    else:
        logger.debug(f'[SCROLL] Drag retornou: {ret}')
    return ret


def not_found_handler(DEVICE):
    logger.debug('[not_found_handler]')
    if DEVICE(text='Não foi possível exportar a conversa.').exists:
        logger.error('Não foi possível exportar a conversa anterior')
        DEVICE(text='OK').click()
    else:
        logger.warning(f'[CLICK] x={NEUTRAL_POS[0]}, y={NEUTRAL_POS[1]}')
        DEVICE.click(*NEUTRAL_POS)  # Clica num local "neutro" para fechar popup

    # TODO: fazer um 'screen_dump' e estudar uma estratégia de retorno.


def install_all():
    for apkfile in __apks.keys():
        install_apk(apkfile)


def init():
    logger.info('Conectando ao dispositivo')  # SERIAL...
    dinfo = DEVICE.info

    if dinfo['currentPackageName'].find('com.whatsapp') == -1:
        raise ExportException('É necessário abrir o aplicativo WhatsApp')

    if not dinfo['naturalOrientation']:
        DEVICE.orientation = 'n'
        DEVICE.freeze_rotation()


def find_element_and_click(element_str):
    """element_str -- dicionário com uiautomator selector"""
    element_obj = find_element(element_str)
    click_ret = element_obj.click.wait(timeout=10000)
    logger.debug(f'[CLICK] {click_ret}')
    return click_ret


def check_screen_and_click(screen, element=None, wait_time=0.0):
    """Verifica se a tela no dispositivo é a informada
    então clica na elemento determinado
    wait_time -- tempo em milisegundos
    Retorna o resultado da ação"""

    if not element:
        element = SCREEN_NEXT_SELECTOR[screen]
    if not isinstance(element, tuple):
        element = (element, )

    click_ret = False

    wait_time /= 1000
    loop_time = 0.3
    elapsed = 0.0

    while elapsed <= wait_time:
        index, screen_found = is_from_screen(screen_dump(), screen)
        if screen_found:
            click_ret = find_element_and_click(element[index])
            break
        logger.debug(f'Aguardando {loop_time} ms para tentar novamente')
        time.sleep(loop_time)
        elapsed += loop_time
    else:
        logger.debug(f'Tela não confere: {screen.name}. Nenhuma ação realizada.')

    return click_ret


def scroll_export_app_list():
    """Verifica qual estratégia de scroll realizar, configura e executa"""
    global APP_SCROLL_RESOLVER
    if APP_SCROLL_RESOLVER == ResolverType.NOTDEFINED:
        screendump = screen_dump()
        logger.debug('Lista de aplicativos: Tipo de scroll ainda não definido')
        APP_SCROLL_RESOLVER = next((r for r in ResolverType if is_from_screen(screendump, r)[1]), None)
        logger.debug('Lista de aplicativos: Scroll é do tipo {APP_SCROLL_RESOLVER}')

    scroll_ret = False
    element = find_element(SCREEN_NEXT_SELECTOR[APP_SCROLL_RESOLVER])

    if not element:
        logger.debug('Elemento encontrado. Não é possível realizar "scroll"')
        return False

    if APP_SCROLL_RESOLVER == ResolverType.LIST:
        logger.debug(f'[SCROLL] vertical')
        scroll_ret = element.scroll.vert()
    else:  # APP_SCROLL_RESOLVER == ResolverType.PAGE:
        logger.debug(f'[SCROLL] horizontal')
        scroll_ret = element.scroll.horiz()

    return scroll_ret


def export_error(screen_dump=None):
    timestr = time.strftime("%Y%m%d-%H%M%S")
    filename = f'Erro - {timestr}.png'
    DEVICE.screenshot(filename)
    logger.error(f'Erro de exportação. Verificar tela capturada em "{filename}"')
    if __logging_level == logging.DEBUG and screen_dump:
        logger.debug(f'Tela desconhecida. DUMP: {xml.etree.ElementTree.tostring(screen_dump,encoding="unicode")}')
    # raise ExportException('Tela desconhecida.')


def export_conversation_inside():
    """A partir da tela da conversa realiza a exportação"""
    initial_screens = [
        Screen.CHAT,
        Screen.CHAT_OPTION,
    ]

    try:
        for s in initial_screens:
            logger.info(f'[TELA] {s}')
            ret = check_screen_and_click(s)
            if not ret:
                logger.warning('Não foi possível exportar esta conversa')
                return False
    except JsonRPCError as e:
        if 'Illegal character' in e.message:
            logger.warning('BUG no Android não permite exportar esta conversa. É necessário exportá-la pela tela.')
            return False

    if not check_screen_and_click(Screen.CHAT_OPTION_PLUS):
        logger.info('Não há opção para exportar esta conversa')
        DEVICE.click(*NEUTRAL_POS)
        return False

    # if not check_screen_and_click(Screen.CHAT_INCLUDE_MEDIA, wait_time=4000):
    if wait_screen(Screen.CHAT_INCLUDE_MEDIA):
        find_element_and_click(SCREEN_NEXT_SELECTOR[Screen.CHAT_INCLUDE_MEDIA])
    else:
        logger.info('Não há mídias para incluir')

    _, modal = is_from_screen(screen_dump(), Screen.MODAL_INICIALIZANDO)
    if modal:
        # element = find_element(SCREEN_NEXT_SELECTOR[Screen.MODAL_INICIALIZANDO])
        logger.info(f'[TELA] Aguardando "Inicializando..."')
        wait_screen(Screen.CHAT_SEND_BY, timeout=40000)
        # element.wait.gone(timeout=40000)

    for i in range(2):
        if check_screen_and_click(Screen.CHAT_SEND_BY_MATCH_APP):
            break
        else:
            logger.info(f'[TELA] Email Bkp não aparece na lista. Realizando "scroll"')
            scroll_export_app_list()
    else:
        logger.error('Não foi possível encontrar o aplicativo de exportação')
        raise ExportException('Não foi possível encontrar o aplicativo de exportação')
        # DEVICE.click(*NEUTRAL_POS)
        # return False

    logger.info(f'[TELA] Aguardando gerenciador de arquivos')
    wait_screen(Screen.FILECHOOSER_GENERIC, timeout=10000)

    other_screen = None
    while other_screen != Screen.EMAILBKP_OK:
        dump = screen_dump()
        _, other_screen = detect_screen(dump)

        if other_screen == Screen.NONE:
            export_error()
            return False

        logger.info(f'[TELA] {other_screen}')
        check_screen_and_click(other_screen)

    wait_screen(Screen.CHAT)
    logger.info('Conversa exportada')


def export_conversation(element):
    """element -- Selector da conversa"""
    element.click.wait()  # Entra na conversa
    export_conversation_inside()
    back_to_chat_list()


def do_the_work():
    # Variáveis utilizadas para gerenciar a fila de exportação
    _exported_chats = set()  # Conjunto com o título das conversas já exportadas
    _current_chats = set()  # Conjunto com o título das conversas que estão na tela
    _chats_queue = OrderedDict()  # Fila das conversas a serem exportadas no turno

    _chat_list = []  # retorno de "get_chat_list()"
    _chat_list_length = 0
    _step_size = 0  # Quanto da lista de mensagens vai ser extraída antes do próx. scroll

    DEVICE.handlers.on(not_found_handler)

    def update_variables(add_all=False):
        """update_variables"""
        """A partir da _chat_list, verifica o conjunto das conversas que já foram extraídas
        e atualiza as filas para um novo turno de extração.
        add_all -- Desconsidera o _step_size e adiciona toda a lista de conversas restantes"""

        _current_chats.clear()
        _chats_queue.clear()

        _chat_list_length = len(_chat_list)
        _step_size = _chat_list_length if add_all else round(_chat_list_length / 2)  # metade da tela por vez

        logger.debug(f'Atualizando fila de mensagens. Quantidade para exportar: {_step_size}')

        ctmp = OrderedDict({c.text: c for c in islice(_chat_list, _step_size)})
        _current_chats.update(ctmp.keys())

        logger.debug(f'Atualizando fila de mensagens. Lista a ser verificada: {_current_chats}')
        logger.debug(f'Atualizando fila de mensagens. Mensagens já exportadas: {_exported_chats}')

        not_exported_yet = _current_chats - _exported_chats
        _chats_queue.update({i: ctmp[i] for i in ctmp if i in not_exported_yet})

        logger.debug(f'Fila de mensagem no turno: {_chats_queue.keys()}')

    def scroll_list():
        """scroll_list"""
        nonlocal _chat_list
        scroll_s = _step_size / len(_chat_list) if _step_size else 0.4
        scroll_chat_list(_chat_list, scroll_s)
        _chat_list = get_chat_list()
        update_variables()

    # Estratégias a executar antes de parar a extração
    update_var_all_chat = partial(update_variables, add_all=True)
    update_var_all_chat.__doc__ = 'update_variables(add_all=True)'

    final_strategies = [
        scroll_list,  # Rola a tela mais uma vez
        update_var_all_chat  # Pega todas as mensagens que estão na tela
    ]

    current_strategy = iter(final_strategies)

    _last_chats_in_screen = set()

    _chat_list = get_chat_list()
    update_variables()

    while True:
        # Condições de parada
        if _current_chats == _last_chats_in_screen:
            try:
                logger.debug('Não há conversas ainda por extrair na última tela')
                strategy = next(current_strategy)
                logger.debug(f'Executando estratégia "{strategy.__doc__}"')
                strategy()
                continue
            except StopIteration:
                break

        _last_chats_in_screen = _current_chats.copy()

        if len(_chats_queue):
            # Há mensagens, retorna ao início da lista de estratégias finais
            logger.debug('Resetando o iterador de estratégias finais')
            current_strategy = iter(final_strategies)

        for contact, chat in _chats_queue.items():
            logger.info(f'Exportando conversa: {contact}')
            export_conversation(chat)
            _exported_chats.add(contact)

        # Avança na lista de conversas
        scroll_list()

    logger.info(f'Fim da exportação. Conversas exportadas: {_exported_chats}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='zapzap_exporter',
        description='Exporta interativamente as conversas do WhatsApp'
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--install', help='Somente instala os aplicativos necessários', action='store_true')
    group.add_argument('--uninstall', help='Somente remove os aplicativos que foram instalados', action='store_true')
    group.add_argument('--info', help='Somente imprime informações do dispositivo', action='store_true')

    parser.add_argument('--debug', help='Ativa mensagens de debug no log de arquivo', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.install:
        install_all()
    elif args.uninstall:
        clean_up()
    elif args.info:
        print('Buscando informações no dispositivo...')
        print(DEVICE.info)
    else:
        init()
        do_the_work()


def test_xpath(xpath):
    """TODO: Refatorar como teste"""
    import os, glob
    from lxml import etree

    def verify_unique_lxml(xpath):
        for f in glob.glob('uiautomator_views/*.uix'):
            root = etree.parse(f).getroot()
            print(f)
            print(root.findall(xpath))

    def verify_unique(xpath):
        for f in glob.glob('uiautomator_views/*.uix'):
            root = xml.etree.ElementTree.parse(f).getroot()
            print(f)
            print(root.findall(xpath))

    tela = Screen.FILECHOOSER_GENERIC
    # xpath = SCREEN_XPATH_SEARCH_ID[tela]
    # xpath = './/*[@resource-id="android:id/resolver_page"]'
    print(xpath)
    verify_unique(xpath)
