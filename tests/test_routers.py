'''
Tests class ConsultarAtributo
'''

from datetime import datetime, timedelta

from exati_routers import ExatiSession, ConsultarAtributos, IDsParqueServico, AtendimentosPendentesRealizados
from exati_routers import AtendimentoPorPontoServico


def test_attribute_name():
    '''
    Tests for ConsultarAtributos
    '''
    with ExatiSession() as session:
        attributes = ConsultarAtributos(session=session)
        assert 'Bairro' in attributes.name_to_records()


def test_ids_parque_servico():
    '''
    Tests for IDsParqueServico
    '''
    with ExatiSession() as session:
        attributes_names = ['Bairro', 'Marco']
        filtro = '377;4;Jabotiana|394;0;407'
        name_to_attribute = ConsultarAtributos(session=session).name_to_records()
        atb_ids = [(name_to_attribute[name]['ID_ATRIBUTO']) for name in attributes_names]
        ps = IDsParqueServico(session=session)
        first_record = ps.export(atb_ids=atb_ids, filtros=filtro)[0]
        print(first_record.keys())
        assert 'BAIRRO' in first_record and 'MARCO' in first_record


def test_atendimento_pendente_realizado():
    '''
    Tests for Atendimento Pendente Realizado
    '''
    today = datetime.today()
    last_day = today - timedelta(days=1)
    with ExatiSession() as session:
        pendentes_realizados = AtendimentosPendentesRealizados(session=session)
        pendentes = pendentes_realizados.export(
            data_inicio=last_day.strftime('%d/%m/%Y'),
            data_final=today.strftime('%d/%m/%Y'),
            status=0
        )
        assert 'DATA_OCORRENCIA' in pendentes[0]
        realizados = pendentes_realizados.export(
            data_inicio=last_day.strftime('%d/%m/%Y'),
            data_final=today.strftime('%d/%m/%Y'),
            status=1
        )
        assert 'DATA_ATENDIMENTO' in realizados[0]


def test_atendimento_por_ponto_servico():
    '''
    Testing router Atendimento Por Ponto Servico
    '''
    with ExatiSession() as session:
        atendimento_ps = AtendimentoPorPontoServico(session=session)
        result = atendimento_ps.get_status_motivo_date(ps=68582)
        assert isinstance(result[- 1], datetime)
