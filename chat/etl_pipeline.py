"""
ETL Pipeline для обработки документов
unstructured + Dask для параллельной обработки
"""
from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean, group_broken_paragraphs
import dask.bag as db
from dask.distributed import Client
import pandas as pd
from typing import List, Dict
import logging
from pathlib import Path
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentETLPipeline:
    #ETL конвейер в стиле Big Data

    def __init__(self, num_workers: int = 2):
        self.num_workers = num_workers
        self.client = Client(n_workers=num_workers, threads_per_worker=2)
        logger.info(f"🚀 Dask кластер запущен")

    def extract(self, file_paths: List[str]) -> db.Bag:
        """EXTRACT: Извлечение данных"""
        logger.info(f"📥 Extract: {len(file_paths)} файлов")
        bag = db.from_sequence(file_paths, npartitions=self.num_workers)

        def read_file(filepath):
            try:
                elements = partition(filename=filepath)
                return {'filepath': filepath, 'elements': elements, 'status': 'success'}
            except Exception as e:
                return {'filepath': filepath, 'error': str(e), 'status': 'failed'}

        return bag.map(read_file)

    def transform(self, extracted_bag: db.Bag) -> db.Bag:
        """TRANSFORM: Очистка и нормализация"""
        logger.info("🔄 Transform: очистка")

        def clean_document(data):
            if data['status'] == 'failed':
                return data

            cleaned_elements = []
            for element in data['elements']:
                if hasattr(element, 'text'):
                    text = clean(element.text, extra_whitespace=True, dashes=True)
                    text = group_broken_paragraphs(text)
                    cleaned_elements.append({
                        'text': text,
                        'type': element.category
                    })

            data['cleaned_elements'] = cleaned_elements
            return data

        return extracted_bag.map(clean_document)

    def load(self, transformed_bag: db.Bag) -> pd.DataFrame:
        """LOAD: Сохранение результатов"""
        logger.info("💾 Load: сбор результатов")

        def flatten_results(data):
            if data['status'] == 'failed':
                return []
            return [{
                'filepath': data['filepath'],
                'text': elem['text'],
                'category': elem['type']
            } for elem in data.get('cleaned_elements', [])]

        flattened = transformed_bag.map(flatten_results).flatten()
        df = flattened.to_dataframe(meta={
            'filepath': 'str', 'text': 'str', 'category': 'str'
        }).compute()

        logger.info(f"✅ Обработано {len(df)} чанков")
        return df

    def run(self, file_paths: List[str]) -> pd.DataFrame:
        """Запуск полного ETL"""
        start_time = time.time()

        extracted = self.extract(file_paths)
        transformed = self.transform(extracted)
        df = self.load(transformed)

        elapsed = time.time() - start_time
        logger.info(f"⏱️ Время обработки: {elapsed:.2f}s")
        logger.info(f" Throughput: {len(file_paths) / elapsed:.1f} файлов/сек")

        return df

    def close(self):
        self.client.close()
        logger.info(" Dask кластер остановлен")
