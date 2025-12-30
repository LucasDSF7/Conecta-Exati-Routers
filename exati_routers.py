'''
Exati routers and session authenticator.
'''

import os
from base64 import b64encode
from time import sleep
from datetime import datetime

import requests
from dotenv import load_dotenv

from exati_dataclasses import Ocorrencia

load_dotenv()


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

    def name_to_records(self, data_inicio: str, data_final: str, status: int, name='ID_OCORRENCIA') -> dict[str, list[dict]]:
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

    def name_to_records(self, name='NOME') -> dict[str, list[dict]]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export()
        return {atb[name]: atb for atb in self.__records}


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

    def export(self, atb_ids: list[str] = None, mat_ids: list[str] = None, filtros: str = '') -> list[dict]:
        '''
        Export records from API.
        Useful attributes filters:
        Relé type == LCU -> 21;0;409
        '''
        atb_ids: list[str] = [] if atb_ids is None else map(str, atb_ids)
        mat_ids: list[str] = [] if mat_ids is None else map(str, mat_ids)
        payload = {
            'CMD_IDS_PARQUE_SERVICO': 1,
            'CMD_COMMAND': 'ConsultarPontosServicos',
            'CMD_SEM_PAGINACAO': 0,
            "CMD_COD_ITEM_ESTRUTURA": ','.join(mat_ids),
            'CMD_ATRIBUTOS_EXPORTACAO': ','.join(atb_ids),
            'CMD_FILTRO_ATRIBUTOS': filtros,
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.__records = response['RAIZ']['PONTOS_SERVICOS']['PONTO_SERVICO']
        return self.__records

    def name_to_records(self, atb_ids: list[str] = None, filtros: str='', name='ID_PONTO_SERVICO')\
        -> dict[str, list[dict]]:
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
            for id_solicitao in ocorrencia.ID_SOLICITACAO:
                payload = {
                    'CMD_ID_SOLICITACAO':id_solicitao,
                    'CMD_COMMAND': 'CancelarElaboracaoSolicitacao',
                    'parser': 'json',
                }
                response = self.session.ex_post(payload=payload, depth=3)
                payload = {
                    'CMD_ID_SOLICITACAO':id_solicitao,
                    'CMD_COMMAND': 'ExcluirSolicitacao',
                    'parser': 'json',
                }
                response = self.session.ex_post(payload=payload, depth=3)
            self.__response_message(response, ocorrencia)

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
