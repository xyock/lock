#!/usr/bin/env python3
"""xyock Workflow - Simple Python version"""

import json
import os
from datetime import datetime


class xyock:
    def __init__(self, file='ai_terms.json'):
        self.file = file
        self.terms = {}
        self.load()
    
    def load(self):
        """파일에서 용어 로드"""
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.terms = data.get('terms', {})
    
    def save(self):
        """파일에 저장"""
        data = {'terms': self.terms, 'updated': datetime.now().isoformat()}
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Saved to {self.file}')
    
    def add(self, word, definition):
        """용어 추가"""
        if word in self.terms:
            print(f'Already exists: {word}')
            return False
        
        self.terms[word] = {
            'definition': definition,
            'created': datetime.now().isoformat(),
            'reviews': 0
        }
        print(f'Added: {word}')
        return True
    
    def delete(self, word):
        """용어 삭제"""
        if word not in self.terms:
            print(f'Not found: {word}')
            return False
        
        del self.terms[word]
        print(f'Deleted: {word}')
        return True
    
    def get(self, word):
        """용어 조회"""
        if word not in self.terms:
            return None
        
        term = self.terms[word]
        term['reviews'] += 1
        return term['definition']
    
    def search(self, query):
        """용어 검색"""
        query = query.lower()
        results = {}
        
        for word, data in self.terms.items():
            if query in word.lower() or query in data['definition'].lower():
                results[word] = data['definition']
        
        return results
    
    def list(self):
        """모든 용어 목록"""
        if not self.terms:
            print('No terms')
            return
        
        print(f'\nTotal: {len(self.terms)} terms\n')
        for word in sorted(self.terms.keys()):
            definition = self.terms[word]['definition']
            print(f'{word}: {definition[:50]}...')
    
    def stats(self):
        """통계"""
        total = len(self.terms)
        reviews = sum(t.get('reviews', 0) for t in self.terms.values())
        
        print(f'\nTotal terms: {total}')
        print(f'Total reviews: {reviews}')
        
        if total > 0:
            most = max(self.terms.items(), key=lambda x: x[1].get('reviews', 0))
            print(f'Most reviewed: {most[0]} ({most[1]["reviews"]} times)')
    
    def export(self, filename):
        """JSON으로 export"""
        data = {word: self.terms[word]['definition'] for word in self.terms}
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Exported to {filename}')
    
    def import_terms(self, filename):
        """JSON에서 import"""
        if not os.path.exists(filename):
            print(f'File not found: {filename}')
            return
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for word, definition in data.items():
            self.add(word, definition)
        
        print(f'Imported from {filename}')


# 사용 예제
if __name__ == '__main__':
    ai = xyock()
    
    # 용어 추가
    ai.add('CNN', 'Convolutional Neural Network')
    ai.add('LSTM', 'Long Short-Term Memory')
    ai.add('RNN', 'Recurrent Neural Network')
    
    # 용어 조회 (복습)
    print('\nReview:')
    print(ai.get('CNN'))
    print(ai.get('LSTM'))
    
    # 검색
    print('\nSearch "neural":')
    results = ai.search('neural')
    for word, definition in results.items():
        print(f'  {word}: {definition}')
    
    # 목록
    ai.list()
    
    # 통계
    ai.stats()
    
    # 저장
    ai.save()
