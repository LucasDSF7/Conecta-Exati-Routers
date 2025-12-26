'''
Tests class ConsultarAtributo
'''

from exati_routers import ExatiSession, ConsultarAtributos, IDsParqueServico


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
