'''
Exati routers and session authenticator.
'''

import os
from base64 import b64encode
from time import sleep
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Ocorrencia:
    '''
    Representa uma Ocorrência do sistema da Exati.
    '''
    ID_PONTO_SERVICO: int = None
    ID_SOLICITACAO: list[int] = None
    ID_OCORRENCIA: int = None
    INDEX_OCORRENCIA_PS: int = None
    ID_TIPO_ORIGEM_OCORRENCIA: int = None
    DESC_TIPO_ORIGEM_OCORRENCIA: str = None
    ID_TIPO_OCORRENCIA: int = None
    SIGLA_PRIORIDADE_PONTO_OCORR: str = None
    DESC_TIPO_OCORRENCIA: str = None
    DATA_LIMITE_ATENDIMENTO: str = None
    HORA_LIMITE_ATENDIMENTO: str = None
    DATA_RECLAMACAO: str = None
    HORA_RECLAMACAO: str = None
    OBS: str = None
    RESULTADO: str = None
    MENSAGEM: str = None

    def header(self) -> list:
        '''
        Cabeçalho
        '''
        return asdict(self).keys()

    def data(self) -> list:
        '''
        Conteudo da data class
        '''
        return asdict(self).values()


@dataclass
class Laudo:
    '''
    Informações de Laudo da Avaliação Técnica
    '''
    DATA: str = None
    ID_LAUDO: int = None
    DESC_LAUDO: str = None
    ID_TIPO_LAUDO: int = None
    DESC_TIPO_LAUDO: str = None
    NUM_AMOSTRAS: int = None
    AVALIADAS: int = None
    ID_EQUIPE: int = None
    DESC_EQUIPE: str = None
    OCORRENCIAS: list[Ocorrencia] = None
    NUM_OCORRENCIAS: int = None
    RESULTADO: str = None
    MENSAGEM: str = None


@dataclass
class PontoServico:
    '''
    Representa um Ponto de Serviço da Exati.
    '''
    ID_PONTO_SERVICO: int = None
    LATITUDE_TOTAL: float = None
    LONGITUDE_TOTAL: float = None


class ExatiSession(requests.sessions.Session):
    '''
    Manage authentication, sessions and a new post request, dealing with Exati responses.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_exati()

    def auth_exati(self):
        '''
        Returns JWT from authentication response
        '''
        basic_auth = f'Basic {b64encode(os.environ.get("EXATI_USER_PASS").encode()).decode()}'
        payload = {
            'CMD_PLATAFORM': 'GUIA',
            'CMD_COMMAND': 'Login',
            'parser': 'json'
        }
        self.headers = {'Authorization': basic_auth}
        response = self.ex_post(payload=payload)
        jwt = response['RAIZ']['AUTH_TOKEN']
        self.headers = {'Authorization': jwt}

    def ex_post(self, payload: dict, depth=1, warnings=True):
        '''
        Modification to post method to handle Exati post requests.
        '''
        response = self.post(url=os.environ.get('EXATI_URL'), data=payload).json()
        try:
            message = response['RAIZ']['MESSAGES']['ERRORS']
        except KeyError:
            if warnings:
                print(f'KeyError de RAIZ, {response}')
            response = self.ex_post(payload=payload, depth=depth + 1, warnings=warnings)
            message = response['RAIZ']['MESSAGES']['ERRORS']
        if message:
            if warnings:
                print(f'{message}, depth = {depth}')
            if depth > 3:
                return response
            sleep(0.25)
            response = self.ex_post(payload=payload, depth=depth + 1, warnings=warnings)
        return response


class AtendimentosPendentesRealizados():
    '''
    Router Atendimentos Pendentes Realizados.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    def export(self, data_inicio: str, data_final: str, status: int) -> list[dict]:
        '''
        Export records from API.
        data_inicio and data_final format -> %d/%m/%Y
        status -> 0 = Pendente. 1 = Realizado. - 1 = Todos.
        '''
        payload = {
            'CMD_ID_PARQUE_SERVICO': 1,
            'CMD_DATA_INICIO': data_inicio,
            'CMD_DATA_CONCLUSAO': data_final,
            'CMD_STATUS': status,
            'CMD_COMMAND': 'ConsultarStatusAtendimentoPontoServico',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.records = response['RAIZ']['PONTOS_STATUS_ATENDIMENTO']['PONTO_STATUS_ATENDIMENTO']
        return self.records

    def name_to_records(self, data_inicio: str, data_final: str, status: int, name='ID_OCORRENCIA') -> dict[str, dict]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export(data_inicio, data_final, status)
        return {atb[name]: atb for atb in self.records}


class AtendimentoPorPontoServico():
    '''
    Router Atendimento por Ponto de Serviço.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    def export(self, ps: int) -> list[dict]:
        '''
        Export records from API.
        ps = ID_PONTO_SERVICO.
        first index from records is the newest record.
        '''
        payload = {
            'CMD_ID_PARQUE_SERVICO': 1,
            'CMD_ID_PONTO_SERVICO': ps,
            'CMD_COMMAND': 'ConsultarAtendimentoPorPontoServico',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        try:
            self.records = response['RAIZ']['ATENDIMENTOS']['ATENDIMENTO']
        except KeyError:
            self.records = [{}]
        return self.records

    def get_status_motivo_date(self, ps: int) -> tuple[str, str, datetime]:
        '''
        Return a tuple with information about status, motivo and date.
        '''
        record = self.export(ps)[0]
        try:
            return record['DESC_STATUS_ATENDIMENTO_PS'],\
        record['DESC_MOTIVO_ATENDIMENTO_PS'],\
        datetime.strptime(record['DATA_ATENDIMENTO'], '%d/%m/%Y')
        except KeyError:
            return 'Pendente', 'Pendente', datetime.strptime('01/07/2021', '%d/%m/%Y')


class AtualizarObs():
    '''
    Router Atualizar Observação
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    def mudar(self, ocorrencia: Ocorrencia, nova_obs: str):
        '''
        Atualiza a obs de uma
        '''
        ocorrencia.OBS = nova_obs
        payload = {
            'CMD_ID_OCORRENCIA': ocorrencia.ID_OCORRENCIA,
            'CMD_INDEX_OCORRENCIA_PS': 1,
            'CMD_OBSERVACOES': ocorrencia.OBS,
            'CMD_COMMAND': 'AtualizarObsPontoOcorrencia',
            'parser': 'json'
        }
        self.session.ex_post(payload=payload)

    def atualizar_reabertura(self, ocorrencia: Ocorrencia):
        '''
        Troca um texto {replace} para um texto novo {text_replace}.
        '''
        ocorrencia.OBS = ocorrencia.OBS.replace('Reabertura', f'{ocorrencia.DESC_STATUS_ATENDIMENTO_REABERTO} {ocorrencia.DESC_MOTIVO_REABERTURA}')
        payload = {
            'CMD_ID_OCORRENCIA': ocorrencia.ID_OCORRENCIA,
            'CMD_INDEX_OCORRENCIA_PS': 1,
            'CMD_OBSERVACOES': ocorrencia.OBS,
            'CMD_COMMAND': 'AtualizarObsPontoOcorrencia',
            'parser': 'json'
        }
        self.session.ex_post(payload=payload)


class ConsultarAmostraLaudo():
    '''
    Router Consultar Amostra Laudo
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    def export(self, laudo: Laudo) -> list[dict]:
        '''
        Export records from API.
        '''
        payload = {
            'CMD_ID_LAUDO': laudo.ID_LAUDO,
            'CMD_AGRUPADO': 0,
            'CMD_CONSULTA_MAPA': 1,
            'CMD_COMMAND': 'ConsultarAmostraLaudo',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.records = response['RAIZ']['AMOSTRAS_LAUDO']['AMOSTRA_LAUDO']
        return self.records

    def get_ocorrencias(self, ids_to_ocorrencia: dict[list], laudo: Laudo) -> list[Ocorrencia]:
        '''
        Needs dependency injection from Laudo.
        '''
        ocorrencias: list[Ocorrencia] = []
        self.export(laudo=laudo)
        for record in self.records:
            if record['POSSUI_OCORRENCIA'] == 1:
                ocorrencias.extend(self.__split_ocorrencia(record['ID_OCORRENCIA'].split(','), ids_to_ocorrencia))
        return ocorrencias

    def __split_ocorrencia(self, ids_ocorrencias: list[str], ids_to_ocorrencia: dict[list]):
        '''
        Split ocorrencia record
        '''
        ocorrencias: list[Ocorrencia] = []
        for id_ocorrencia in ids_ocorrencias:
            record: dict = ids_to_ocorrencia.get(int(id_ocorrencia.strip()), {})
            ocorrencia = Ocorrencia()
            ocorrencia.ID_PONTO_SERVICO = record.get('ID_PONTO_SERVICO')
            ocorrencia.ID_OCORRENCIA = record.get('ID_OCORRENCIA', id_ocorrencia)
            ocorrencia.DESC_TIPO_OCORRENCIA = record.get('DESC_TIPO_OCORRENCIA')
            ocorrencias.append(ocorrencia)
        return ocorrencias


class ConsultarAtributos():
    '''
    Router Consultar Atributos.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.__records: list[dict] = None

    @property
    def records(self):
        '''
        Returns private property records.
        '''
        if self.__records is None:
            self.export()
        return self.__records

    def export(self) -> list[dict]:
        '''
        Export records from API.
        '''
        payload = {
            'CMD_COMMAND': 'ConsultarAtributos',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.__records = response['RAIZ']['ATRIBUTOS']['ATRIBUTO']
        return self.__records

    def name_to_records(self, name='NOME') -> dict[str, dict]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export()
        return {atb[name]: atb for atb in self.__records}


class ConsultarEquipes():
    '''
    Router Consultar Equipes
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.__records: list[dict] = None

    @property
    def records(self):
        '''
        Returns private property records.
        '''
        if self.__records is None:
            self.export()
        return self.__records

    def export(self) -> list[dict]:
        '''
        Export records from API.
        '''
        payload = {
            'CMD_ATIVO': 1,
            'CMD_IS_RELATORIO': 0,
            'CMD_MOSTRAR_MEMBROS': 1,
            'CMD_COMMAND': 'ConsultarEquipes',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.__records = response['RAIZ']['EQUIPES']['EQUIPE']
        return self.__records

    def name_to_records(self, name='DESC_EQUIPE') -> dict[str, dict]:
        '''
        Create a dict with key = name of attribute and values = records
        DESC_EQUIPE
        ID_EQUIPE
        '''
        self.export()
        return {atb[name]: atb for atb in self.__records}


class ConsultarHistoricoPontoServico():
    '''
    Router ConsultarHistorico
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    def export(self, ps: int) -> list[dict]:
        '''
        Retorna records com histórico da estrutura de um ponto de serviço.
        Ordenado da mais antiga para a mais nova.
        '''
        payload = {
            'CMD_ID_PONTO_SERVICO': ps,
            'CMD_COMMAND': 'ConsultarHistoricoVersaoPontoServico',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.records = response['RAIZ']['VERSOES']['VERSAO']
        return self.records

    def export_xml(self, id_estrutura: int) -> str:
        '''
        Returns a string with xml format
        '''
        payload = {
            'CMD_ID_ESTRUTURA_PS': id_estrutura,
            'CMD_COMMAND': 'ConsultarItensEstruturaPontoServico',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        return response['RAIZ']['ITEM_ESTRUTURA_PS']


class ConsultarLaudo():
    '''
    Router Consultar Laudo
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.__records: list[dict] = None

    @property
    def records(self):
        '''
        Returns private property records.
        '''
        if self.__records is None:
            self.export()
        return self.__records

    def export(self, **kwargs) -> list[dict]:
        '''
        Export records from API.
        Return dicts that match filters in kwargs.
        kwargs pattern must be key -> tuple. Tuple contains constraints
        for the key.
        Ex.: ID_TIPO_LAUDO: (5,)
        Ex.: ELABORADO: (1,)
        '''
        last_month = (datetime.today() - timedelta(days=30)).strftime('%d/%m/%Y')
        payload = {
            'CMD_ID_PARQUE_SERVICO': 1,
            'CMD_DATA_CRIACAO_INICIAL': last_month,
            'CMD_COMMAND': 'ConsultarLaudo',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        response = response['RAIZ']['LAUDOS']['LAUDO']
        self.__records = [atb for atb in response if all(atb[key] in values for key, values in kwargs.items())]
        return self.__records


class ConsultarSolicitacao():
    '''
    Router Consultar Solicitacao.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    def export(self, data_inicial: datetime, id_origem: str = '', id_status: int = '') -> list[dict]:
        '''
        Export records from API.
        id_status = 3 -> Pendente.
        id_origem = 107 -> Bright City
        '''
        payload = {
            'CMD_IDS_PARQUE_SERVICO': 1,
            'CMD_DATA_RECLAMACAO': data_inicial.strftime('%d/%m/%Y'),
            'CMD_ID_STATUS_SOLICITACAO': id_status,
            'CMD_COMMAND': 'ConsultarSolicitacao',
            'CMD_ID_TIPO_ORIGEM_SOLICITACAO': id_origem,
            'CMD_INCONSISTENCIA': -1,
            'CMD_PENDENTE_APROVACAO': -1,
            'CMD_CONSULTAR_REABERTAS': 0,
            'CMD_SOMENTE_VINCULADOS': 0,
            'CMD_PAGE_SIZE': 5000,
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.records = response['RAIZ']['SOLICITACOES']['SOLICITACAO']
        return self.records


class IDsParqueServico():
    '''
    Router IDs Parque Servico.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.__records: list[dict] = None

    @property
    def records(self):
        '''
        Returns private property records.
        '''
        if self.__records is None:
            self.export()
        return self.__records

    def export(self, atb_ids: list[str] = None, mat_id: str = '', filtros: str = '') -> list[dict]:
        '''
        Export records from API.
        Useful attributes filters:
        Relé type == LCU -> 21;0;409
        '''
        atb_ids: list[str] = [] if atb_ids is None else map(str, atb_ids)
        payload = {
            'CMD_IDS_PARQUE_SERVICO': 1,
            'CMD_COMMAND': 'ConsultarPontosServicos',
            'CMD_SEM_PAGINACAO': 0,
            "CMD_ID_ITEM": mat_id,
            'CMD_ATRIBUTOS_EXPORTACAO': ','.join(atb_ids),
            'CMD_FILTRO_ATRIBUTOS': filtros,
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.__records = response['RAIZ']['PONTOS_SERVICOS']['PONTO_SERVICO']
        return self.__records

    def name_to_records(self, atb_ids: list[str] = None, filtros: str='', name='ID_PONTO_SERVICO')\
        -> dict[str, dict]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export(atb_ids, filtros)
        return {atb[name]: atb for atb in self.__records}


class PrioridadeTipoOcorrencia():
    '''
    Router for get info about ocorrencia priority
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.__caching = {}

    def add_priority(self, ocorrencia: Ocorrencia):
        '''
        Add property SIGLA_PRIORIDADE_PONTO_OCORR to Ocorrencia
        '''
        if ocorrencia.ID_TIPO_OCORRENCIA not in self.__caching:
            payload = {
            'CMD_ID_TIPO_OCORRENCIA': ocorrencia.ID_TIPO_OCORRENCIA,
            'CMD_COMMAND': 'ConsultarPrioridadeTipoOcorrencia',
            'parser': 'json'
            }
            response = self.session.ex_post(payload=payload)
            ocorrencia.SIGLA_PRIORIDADE_PONTO_OCORR = response['RAIZ']\
                ['PRIORIDADES_TIPO_OCORRENCIA']\
                    ['PRIORIDADE_TIPO_OCORRENCIA'][0]['SIGLA_PRIORIDADE_PONTO_OCORR']
            self.__caching[ocorrencia.ID_TIPO_OCORRENCIA] = ocorrencia.SIGLA_PRIORIDADE_PONTO_OCORR
        else:
            ocorrencia.SIGLA_PRIORIDADE_PONTO_OCORR = self.__caching[ocorrencia.ID_TIPO_OCORRENCIA]


class SalvarExcluirOcorrencia():
    '''
    Router for saving a new Ocorrencia in Exati API.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session

    def save(self, ocorrencias: list[Ocorrencia], prioridade: PrioridadeTipoOcorrencia):
        '''
        Create in Exati - save - Ocorrencia from a list of Ocorrencia.
        '''
        for ocorrencia in ocorrencias:
            if self.__check_invalid_ocorrencia_propertys(ocorrencia):
                continue
            prioridade.add_priority(ocorrencia=ocorrencia)
            payload = {
                'CMD_ID_PONTO_SERVICO': ocorrencia.ID_PONTO_SERVICO,
                'CMD_DATA_RECLAMACAO': ocorrencia.DATA_RECLAMACAO,
                'CMD_HORA_RECLAMACAO': ocorrencia.HORA_RECLAMACAO,
                'CMD_ID_TIPO_ORIGEM_OCORRENCIA': ocorrencia.ID_TIPO_ORIGEM_OCORRENCIA,
                'CMD_ID_TIPO_OCORRENCIA': ocorrencia.ID_TIPO_OCORRENCIA,
                'CMD_COMMAND': 'SalvarSolicitacaoPontoServico',
                'CMD_OBS': ocorrencia.OBS,
                'CMD_SIGLA_PRIORIDADE_PONTO_OCORR': ocorrencia.SIGLA_PRIORIDADE_PONTO_OCORR,
                'parser': 'json',
            }
            response = self.session.ex_post(payload=payload)
            self.__response_message(response, ocorrencia)

    def delete(self, ocorrencias: list[Ocorrencia]):
        '''
        Delete in Exati Ocorrencia from a list of Ocorrencia
        '''
        for ocorrencia in ocorrencias:
            if self.__check_reopen(ocorrencia) or self.__check_reprogramacao(ocorrencia):
                continue
            for id_solicitao in ocorrencia.ID_SOLICITACAO:
                payload = {
                    'CMD_ID_SOLICITACAO':id_solicitao,
                    'CMD_COMMAND': 'CancelarElaboracaoSolicitacao',
                    'parser': 'json',
                }
                response = self.session.ex_post(payload=payload)
                payload = {
                    'CMD_ID_SOLICITACAO':id_solicitao,
                    'CMD_COMMAND': 'ExcluirSolicitacao',
                    'parser': 'json',
                }
                response = self.session.ex_post(payload=payload)
            self.__response_message(response, ocorrencia)

    def __check_invalid_ocorrencia_propertys(self, ocorrencia: Ocorrencia) -> bool:
        '''
        Check Ocorrencia propertys to asserty corret api call
        '''
        ocorrencia.OBS = '' if ocorrencia.OBS is None else ocorrencia.OBS
        if ocorrencia.DATA_RECLAMACAO is None or ocorrencia.HORA_RECLAMACAO is None:
            ocorrencia.MENSAGEM = 'Necessário preencher data e hora para criar ocorrência.'
            ocorrencia.RESULTADO = 'NOK'
            return True
        if ocorrencia.ID_PONTO_SERVICO is None:
            ocorrencia.MENSAGEM = 'Necessário fornecer ID do ponto de serviço.'
            ocorrencia.RESULTADO = 'NOK'
            return True
        if ocorrencia.ID_TIPO_OCORRENCIA is None or ocorrencia.ID_TIPO_ORIGEM_OCORRENCIA is None:
            ocorrencia.MENSAGEM = 'Necessário preencher qual o tipo e origem da ocorrência.'
            ocorrencia.RESULTADO = 'NOK'
            return True
        return False

    def __check_reopen(self, ocorrencia: Ocorrencia) -> bool:
        '''
        Checks if a Ocorrencia has "impossibilidade".
        '''
        for id_solicitao in ocorrencia.ID_SOLICITACAO:
            payload = {
                'CMD_ID_SOLICITACAO':id_solicitao,
                'CMD_COMMAND': 'ConsultarDetalhesSolicitacao',
                'parser': 'json',
            }
            response = self.session.ex_post(payload=payload)
            num_reopen = response['RAIZ']['SOLICITACAO'].get('POSSUI_ATENDIMENTO_ANTERIOR', 0)
            if int(num_reopen) >= 1:
                ocorrencia.MENSAGEM = 'Solicitação possui reabertura. Não foi possível excluir.'
                ocorrencia.RESULTADO = 'NOK'
                return True
        return False

    def __check_reprogramacao(self, ocorrencia: Ocorrencia) -> bool:
        '''
        Checks if a Ocorrencia has "reprogramação".
        '''
        payload = {
            'CMD_ID_OCORRENCIA':ocorrencia.ID_OCORRENCIA,
            'CMD_COMMAND': 'ConsultarPontosServicoOcorrenciaNovo',
            'parser': 'json',
        }
        response = self.session.ex_post(payload=payload)
        record = response['RAIZ']['PONTOS_SERVICOS_OCORRENCIA']['PONTO_SERVICO_OCORRENCIA'][0]
        if 'ID_REPROGRAMACAO_ATUAL' in record:
            ocorrencia.MENSAGEM = 'Ocorrência possui reabertura. Não foi possível excluir.'
            ocorrencia.RESULTADO = 'NOK'
            return True
        return False

    def __response_message(self, response, ocorrencia: Ocorrencia):
        '''
        Adds response message to Ocorrencia object.
        '''
        try:
            response = response['RAIZ']['MESSAGES']
        except (KeyError, TypeError):
            ocorrencia.RESULTADO = 'NOK'
            ocorrencia.MENSAGEM = 'Erro não identificado.'
            return
        if response['INFORMATIONS']:
            ocorrencia.RESULTADO = 'OK'
            ocorrencia.MENSAGEM = response['INFORMATIONS'][- 1]
            return
        ocorrencia.RESULTADO = 'NOK'
        ocorrencia.MENSAGEM = f'Erro: {response["ERRORS"][- 1]}'


class TipoOcorrencia():
    '''
    Router Tipo Ocorrencia.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.__records: list[dict] = None

    @property
    def records(self):
        '''
        Returns private property records.
        '''
        if self.__records is None:
            self.export()
        return self.__records

    def export(self) -> list[dict]:
        '''
        Export records from API.
        '''
        payload = {
            'CMD_ID_PARQUE_SERVICO': 1,
            'CMD_COMMAND': 'ConsultarTipoOcorrencia',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.__records = response['RAIZ']['TIPOS_OCORRENCIA']['TIPO_OCORRENCIA']
        return self.__records

    def name_to_records(self, name='DESC_TIPO_OCORRENCIA') -> dict[str, dict]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export()
        return {atb[name]: atb for atb in self.__records}
