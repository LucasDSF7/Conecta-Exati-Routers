'''
Some structures from Exati are better represented by dataclass.
Property names are igual to those in API responses, making easer to
 feed responses into the dataclass using python setattr and getattr functions.
'''

from dataclasses import dataclass, asdict

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
