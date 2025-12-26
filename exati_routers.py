'''
Exati routers and session authenticator.
'''

import os
from base64 import b64encode
from time import sleep

import requests
from dotenv import load_dotenv
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


class ConsultarAtributos():
    '''
    Router Consultar Atributos.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records: list[dict] = None

    @property
    def records(self):
        '''
        Assuring that property records is not None.
        '''
        if self.records is None:
            self.export()
        return self.records

    def export(self) -> list[dict]:
        '''
        Export records from API.
        '''
        payload = {
            'CMD_COMMAND': 'ConsultarAtributos',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.records = response['RAIZ']['ATRIBUTOS']['ATRIBUTO']

    def name_to_records(self, name='NOME') -> dict[str, list[dict]]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export()
        return {atb[name]: atb for atb in self.records}


class IDsParqueServico():
    '''
    Router IDs Parque Servico.
    '''
    def __init__(self, session: ExatiSession):
        self.session = session
        self.records = None

    @property
    def records(self):
        '''
        Assuring that property records is not None.
        '''
        if self.records is None:
            self.export()
        return self.records

    def export(self, atb_ids: list[str] = None, filtros: str = '') -> list[dict]:
        '''
        Export records from API.
        '''
        if atb_ids is None:
            atb_ids: list[str] = []
        payload = {
            'CMD_IDS_PARQUE_SERVICO': 1,
            'CMD_COMMAND': 'ConsultarPontosServicos',
            'CMD_SEM_PAGINACAO': 0,
            'CMD_ATRIBUTOS_EXPORTACAO': ','.join(atb_ids),
            'CMD_FILTRO_ATRIBUTOS': filtros,
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        self.records = response['RAIZ']['PONTOS_SERVICOS']['PONTO_SERVICO']

    def name_to_records(self, atb_ids: list[str] = None, filtros: str='', name='ID_PONTO_SERVICO')\
        -> dict[str, list[dict]]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        self.export(atb_ids, filtros)
        return {atb[name]: atb for atb in self.records}
