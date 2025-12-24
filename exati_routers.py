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
        if message and warnings:
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

    def export(self) -> list[dict]:
        '''
        Export records from API.
        '''
        payload = {
            'CMD_COMMAND': 'ConsultarAtributos',
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        return response['RAIZ']['ATRIBUTOS']['ATRIBUTO']

    def name_to_records(self, name='NOME') -> dict[str, list[dict]]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        records = self.export()
        return {atb[name]: atb for atb in records}


class IDsParqueServico():
    '''
    Router IDs Parque Servico.
    '''
    def __init__(self, session: ExatiSession, atributos: ConsultarAtributos):
        self.session = session
        self.atributos = atributos

    def export(self, names_attributes: list[str], filtros: str) -> list[dict]:
        '''
        Export records from API.
        '''
        attributes_records = self.atributos.name_to_records()
        atb_ids: list[str] = []
        for name in names_attributes:
            try:
                atb_ids.append(str(attributes_records[name]['ID_ATRIBUTO']))
            except KeyError:
                print(f'Attribute {name} not in the records')
        payload = {
            'CMD_IDS_PARQUE_SERVICO': 1,
            'CMD_COMMAND': 'ConsultarPontosServicos',
            'CMD_SEM_PAGINACAO': 0,
            'CMD_ATRIBUTOS_EXPORTACAO': ','.join(atb_ids),
            'CMD_FILTRO_ATRIBUTOS': filtros,
            'parser': 'json'
        }
        response = self.session.ex_post(payload=payload)
        return response['RAIZ']['PONTOS_SERVICOS']['PONTO_SERVICO']

    def name_to_records(self, names_attributes: list[str], filtros: str, name='ID_PONTO_SERVICO')\
        -> dict[str, list[dict]]:
        '''
        Create a dict with key = name of attribute and values = records
        '''
        records = self.export(names_attributes, filtros)
        return {atb[name]: atb for atb in records}
