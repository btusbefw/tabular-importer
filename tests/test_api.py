import io
import json
import unittest
from datetime import time
from unittest.mock import patch
import openpyxl
from fastapi.testclient import TestClient
from api import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {'x-importer-client': 'local-ui'}
        self.rules = [{'name': 'id', 'required': True}, {'name': 'amount', 'type': 'decimal'}]

    def send(self, content=b'id;amount\n001;12.50\n002;broken\n', filename='input.csv', **fields):
        return self.client.post('/api/import', headers=self.headers,
                                files={'file': (filename, content)},
                                data={'schema': json.dumps(self.rules), **fields})

    def test_upload_preview_and_csv_export(self):
        response = self.send()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['headers'], ['id', 'amount'])
        self.assertEqual(data['invalid'], 1)
        self.assertEqual(data['rows'][0]['normalized']['id'], '001')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        exported = self.send(output='csv')
        self.assertEqual(exported.status_code, 200)
        self.assertIn('normalized.csv', exported.headers['content-disposition'])
        self.assertEqual(len(exported.text.splitlines()), 3)

    def test_manual_mapping_upload(self):
        response = self.send(b'Code;Total\n009;18.75\n', mapping=json.dumps({'id': 'Code', 'amount': 'Total'}))
        self.assertEqual(response.json()['rows'][0]['normalized'], {'id': '009', 'amount': '18.75'})

    def test_xlsx_upload(self):
        book = openpyxl.Workbook(); book.active.append(['id', 'amount']); book.active.append(['004', 9])
        data = io.BytesIO(); book.save(data); book.close()
        response = self.send(data.getvalue(), 'input.xlsx')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['rows'][0]['normalized']['amount'], '9')

    def test_malformed_inputs_are_client_errors(self):
        for fields in [{'schema': 'not json'}, {'schema': '[{"name":"x","type":"invalid"}]'},
                       {'mapping': '{"id":"absent","amount":"amount"}'}, {'output': 'exe'},
                       {'schema': '[{"name":"x","min":NaN}]'}, {'encoding': 'unknown'}]:
            with self.subTest(fields=fields):
                self.assertEqual(self.send(**fields).status_code, 422)
        self.assertEqual(self.send(b'garbage', 'bad.xlsx').status_code, 422)

    def test_actual_stream_size_is_bounded(self):
        with patch('api.MAX_REQUEST', 20):
            self.assertEqual(self.send().status_code, 413)

    def test_individual_file_size_is_bounded(self):
        with patch('api.MAX_BYTES', 5):
            self.assertEqual(self.send().status_code, 413)

    def test_cross_origin_and_missing_client_header_rejected(self):
        self.assertEqual(self.client.post('/api/import').status_code, 403)
        self.assertEqual(self.client.get('/health', headers={'origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.get('/health', headers={'host': 'evil.example'}).status_code, 400)
        self.assertEqual(self.client.get('/health', headers={'origin': 'http://testserver'}).status_code, 200)

    def test_no_retained_upload_lookup(self):
        self.send()
        self.assertEqual(self.client.get('/uploads/input.csv').status_code, 404)
        self.assertEqual(self.client.get('/health').json()['storage'], 'stateless')

    def test_native_excel_time_serializes_and_normalizes(self):
        book = openpyxl.Workbook(); book.active.append(['duration']); book.active.append([time(2,30)])
        data = io.BytesIO(); book.save(data); book.close()
        response = self.send(data.getvalue(), 'input.xlsx', schema=json.dumps([{'name':'duration','type':'duration'}]))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['rows'][0]['normalized']['duration'], '9000')

    def test_static_interface_is_served_without_external_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="mapping"', response.text)
        self.assertIn("script-src 'self'", response.headers['content-security-policy'])
        self.assertEqual(self.client.get('/app.js').status_code, 200)
        self.assertEqual(self.client.get('/style.css').status_code, 200)
        self.assertEqual(self.client.get('/example/synthetic.csv').status_code, 200)
        self.assertEqual(self.client.get('/example/requirements.txt').status_code, 404)

    def test_invalid_rule_shapes_and_mapping_types(self):
        for rule in [{'name':'x','aliases':{}},{'name':'x','formats':'%Y'},
                     {'name':'x','required':'false'},{'name':'x','values':[]},
                     {'name':'x','min':'NaN'},{'name':'x','min':2,'max':1}]:
            self.assertEqual(self.send(schema=json.dumps([rule])).status_code, 422)
        self.assertEqual(self.send(mapping='[]').status_code, 422)


if __name__ == '__main__':
    unittest.main()
