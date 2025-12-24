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
        attributes = ConsultarAtributos(session=session)
        ps = IDsParqueServico(session=session, atributos=attributes)
        first_record = ps.export(names_attributes=attributes_names, filtros='')[0]
        assert 'BAIRRO' in first_record and 'MARCO' in first_record
