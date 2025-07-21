#!/usr/bin/env python3
"""
DrinkSimples Scrapper Final
Processa receitas direto das URLs
Baixa imagens e gera JSON limpo para BD
"""

# =====================================
# CONFIGURAÇÕES - AJUSTE AQUI
# =====================================

# Site base
BASE_URL = "https://drinksimples.com.br"
URL_PATTERN = "/?p="  # Padrão das URLs: /?p=315

# Range de IDs para buscar receitas (de X até Y)
RANGE_INICIO = 1
RANGE_FIM = 1000

# Pastas para salvar arquivos
PASTA_IMAGENS = "imagens"
PASTA_DADOS = "dados"

# Delay entre requests (segundos) - para não sobrecarregar o servidor
DELAY_REQUESTS = 0.5

# Headers para requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# =====================================
# IMPORTS
# =====================================

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin
# Imports para PDF removidos - não precisamos mais

class DrinkSimplesScrapper:
    """Scrapper que processa receitas direto das URLs"""
    
    def __init__(self):
        self.drinks_data = []
        self.img_folder = PASTA_IMAGENS
        self.data_folder = PASTA_DADOS
        self.session = requests.Session()
        
        self._create_folders()
        self._setup_session()
        
        print("🍹 DrinkSimples Scrapper Final")
        print("=" * 50)
        print(f"🌐 Site: {BASE_URL}")
        print(f"📊 Range: {RANGE_INICIO} até {RANGE_FIM}")
        print("🖼️ Baixa imagens automaticamente")
        print("💾 Gera JSON limpo para BD")
    
    def _create_folders(self):
        """Criar pastas necessárias"""
        os.makedirs(self.data_folder, exist_ok=True)
        os.makedirs(self.img_folder, exist_ok=True)
        print(f"📁 Pastas criadas: {self.data_folder}/ e {self.img_folder}/")
    
    def _setup_session(self):
        """Configurar sessão HTTP para download de imagens"""
        self.session.headers.update(HEADERS)
        self.session.headers.update({
            'Accept': 'image/*,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        })
    
    def download_image(self, image_url, drink_title):
        """Baixar e salvar imagem"""
        try:
            if not image_url:
                return None
            
            print(f"    📥 Baixando imagem: {image_url}")
            
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Detectar extensão
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # Tentar pela URL
                if '.jpg' in image_url.lower():
                    ext = '.jpg'
                elif '.png' in image_url.lower():
                    ext = '.png'
                elif '.webp' in image_url.lower():
                    ext = '.webp'
                else:
                    ext = '.jpg'  # Default
            
            # Nome do arquivo limpo
            clean_title = re.sub(r'[^\w\s-]', '', drink_title).strip()
            clean_title = re.sub(r'[-\s]+', '_', clean_title).lower()
            if not clean_title:
                clean_title = f"drink_{len(self.drinks_data) + 1}"
            
            filename = f"{clean_title}{ext}"
            filepath = os.path.join(self.img_folder, filename)
            
            # Se arquivo existe, adicionar timestamp
            if os.path.exists(filepath):
                timestamp = datetime.now().strftime('%H%M%S')
                filename = f"{clean_title}_{timestamp}{ext}"
                filepath = os.path.join(self.img_folder, filename)
            
            # Salvar imagem
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"    ✅ Imagem salva: {filename}")
            return filename
            
        except Exception as e:
            print(f"    ⚠️ Erro ao baixar imagem: {e}")
            return None
    
    def extract_from_html(self, html_content, url="", drink_id=None):
        """Extrair dados de HTML fornecido"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Estrutura de dados SIMPLIFICADA para BD
        drink_data = {
            'id': drink_id or len(self.drinks_data) + 1,
            'titulo': '',
            'categoria': '',
            'caracteristicas': [],
            'copo': '',
            'origem': '',
            'ingredientes': [],
            'dicas_ingredientes': [],
            'modo_preparo': [],
            'imagem': ''  # Apenas nome do arquivo
        }
        
        # 1. TÍTULO
        title_selectors = [
            'h1', 'h1.entry-title', 'h1.post-title', '.entry-title', '.post-title',
            'h2', 'h3'
        ]
        
        for selector in title_selectors:
            try:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text and len(title_text) > 3 and len(title_text) < 100:
                        drink_data['titulo'] = title_text
                        break
            except:
                continue
        
        # Se não achou, procurar por palavras-chave em qualquer tag
        if not drink_data['titulo']:
            all_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
            for tag in all_tags:
                text = tag.get_text(strip=True)
                if any(keyword in text.lower() for keyword in ['martini', 'caipirinha', 'mojito', 'piña', 'manhattan', 'cosmopolitan']):
                    if 5 <= len(text) <= 50:
                        drink_data['titulo'] = text
                        break
        
        if not drink_data['titulo']:
            print("    ⚠️ Título não encontrado")
            return None
        
        # 2. EXTRAIR DADOS DO TEXTO
        page_text = soup.get_text()
        
        # Categoria
        if 'alcoólico' in page_text.lower():
            drink_data['categoria'] = 'Não Alcoólico' if 'não alcoólico' in page_text.lower() else 'Alcoólico'
        
        # Características
        caracteristicas = ['clássico', 'forte', 'seco', 'doce', 'amargo', 'refrescante', 'cremoso', 'frutado', 'tropical', 'gelado']
        for keyword in caracteristicas:
            if keyword in page_text.lower():
                drink_data['caracteristicas'].append(keyword.title())
        
        # Copo
        copos = ['taça de coquetel', 'taça martini', 'taça', 'copo', 'mixing glass', 'rocks glass', 'highball', 'old fashioned']
        for copo in copos:
            if copo in page_text.lower():
                drink_data['copo'] = copo.title()
                break
        
        # Origem
        origens = ['estados unidos', 'brasil', 'cuba', 'inglaterra', 'frança', 'itália', 'méxico', 'argentina', 'peru', 'jamaica']
        for origem in origens:
            if origem in page_text.lower():
                drink_data['origem'] = origem.title()
                break
        
        # 3. INGREDIENTES
        h3_ingredientes = soup.find('h3', string='Ingredientes')
        if h3_ingredientes:
            next_ul = h3_ingredientes.find_next('ul')
            if next_ul:
                ingredientes = [li.get_text(strip=True) for li in next_ul.find_all('li')]
                drink_data['ingredientes'] = [ing for ing in ingredientes if ing]
                
                # Dicas após ingredientes
                current = next_ul.find_next_sibling()
                dicas = []
                while current and current.name != 'h3':
                    if current.name == 'p':
                        dica_text = current.get_text(strip=True)
                        if len(dica_text) > 20:
                            dicas.append(dica_text)
                    elif current.name == 'blockquote':
                        dica_text = current.get_text(strip=True)
                        if dica_text:
                            dicas.append(dica_text)
                    current = current.find_next_sibling()
                    if not current:
                        break
                
                drink_data['dicas_ingredientes'] = dicas
        
        # 4. MODO DE PREPARO
        h3_preparo = soup.find('h3', string='Preparo')
        if h3_preparo:
            next_ol = h3_preparo.find_next('ol')
            if next_ol:
                preparo_steps = [li.get_text(strip=True) for li in next_ol.find_all('li')]
                drink_data['modo_preparo'] = [step for step in preparo_steps if step]
        
        # 5. IMAGEM (extrair URL e baixar)
        img_url = None
        img_selectors = ['img.wp-post-image', 'img[src*="drink"]', 'img[src*="cocktail"]', 'img']
        
        for selector in img_selectors:
            try:
                if selector == 'img':
                    imgs = soup.find_all('img', src=True)
                    for img in imgs:
                        src = img.get('src', '')
                        if any(keyword in src.lower() for keyword in ['drink', 'cocktail', 'receita', drink_data['titulo'].lower()]):
                            img_url = src
                            break
                else:
                    img_elem = soup.select_one(selector)
                    if img_elem and img_elem.get('src'):
                        img_url = img_elem['src']
                        break
            except:
                continue
        
        # Baixar imagem se encontrada
        if img_url:
            # Resolver URL completa se necessário
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = BASE_URL + img_url
            
            image_filename = self.download_image(img_url, drink_data['titulo'])
            if image_filename:
                drink_data['imagem'] = image_filename
        
        print(f"    ✅ {drink_data['titulo']}: {len(drink_data['ingredientes'])} ingredientes, {len(drink_data['modo_preparo'])} passos")
        return drink_data
    
    def process_text_content(self, text_content, url=""):
        """Processar conteúdo de texto simples"""
        lines = text_content.strip().split('\n')
        html_parts = ['<html><body>']
        
        in_ingredients = False
        in_preparo = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line == 'Ingredientes':
                html_parts.append('<h3>Ingredientes</h3><ul>')
                in_ingredients = True
                in_preparo = False
                continue
            elif line == 'Preparo':
                if in_ingredients:
                    html_parts.append('</ul>')
                html_parts.append('<h3>Preparo</h3><ol>')
                in_ingredients = False
                in_preparo = True
                continue
            elif line in ['Alcoólico', 'Clássico', 'Forte', 'Seco']:
                html_parts.append(f'<span class="caracteristica">{line}</span>')
                continue
            elif 'Taça' in line:
                html_parts.append(f'<span class="copo">{line}</span>')
                continue
            elif 'Estados Unidos' in line:
                html_parts.append(f'<span class="origem">{line}</span>')
                continue
            
            # Título (primeira linha útil)
            if not in_ingredients and not in_preparo and any(char.isalpha() for char in line):
                if len(line) > 3 and not any(word in line for word in ['Tipo', 'Características', 'Copo', 'Origem']):
                    html_parts.append(f'<h1>{line}</h1>')
                    continue
            
            # Ingredientes
            if in_ingredients:
                if any(word in line.lower() for word in ['dose', 'gota', 'cubo', 'azeitona', 'casca', 'ml', 'cl']):
                    html_parts.append(f'<li>{line}</li>')
                else:
                    if in_ingredients:
                        html_parts.append('</ul>')
                        in_ingredients = False
                    html_parts.append(f'<p>{line}</p>')
            
            # Preparo  
            elif in_preparo:
                if any(line.startswith(word) for word in ['Coloque', 'Pingue', 'Em seguida', 'Coe', 'Passe', 'Espete', 'Misture', 'Adicione']):
                    html_parts.append(f'<li>{line}</li>')
                else:
                    html_parts.append(f'<p>{line}</p>')
            
            # Outras linhas
            elif line:
                html_parts.append(f'<p>{line}</p>')
        
        if in_ingredients:
            html_parts.append('</ul>')
        if in_preparo:
            html_parts.append('</ol>')
            
        html_parts.append('</body></html>')
        html_content = '\n'.join(html_parts)
        
        return self.extract_from_html(html_content, url)
    
    def add_recipe(self, content, content_type="html", url=""):
        """Adicionar receita"""
        if content_type == "html":
            drink_data = self.extract_from_html(content, url)
        else:  # text
            drink_data = self.process_text_content(content, url)
        
        if drink_data:
            self.drinks_data.append(drink_data)
            return drink_data
        return None
    
    def save_consolidated_json(self, filename=None):
        """Salvar JSON consolidado"""
        if not self.drinks_data:
            print("❌ Nenhuma receita para salvar")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"drinksimples_completo_{timestamp}.json"
        
        filepath = os.path.join(self.data_folder, filename)
        
        # JSON super simplificado - apenas as receitas
        output_data = self.drinks_data
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 JSON salvo: {filepath}")
        print(f"📊 {len(self.drinks_data)} receitas")
        
        return filepath
    



def process_url_range(scrapper, start=None, end=None):
    """Processar faixa de URLs automaticamente"""
    
    # Usar configurações padrão se não especificado
    if start is None:
        start = RANGE_INICIO
    if end is None:
        end = RANGE_FIM
    
    base_url = f"{BASE_URL}{URL_PATTERN}"
    total_found = 0
    
    print(f"\n🌐 Processando URLs de {start} até {end}")
    print(f"📡 Base: {base_url}")
    print("=" * 50)
    
    for p in range(start, end + 1):
        url = f"{base_url}{p}"
        print(f"\n🔍 [{p}/{end}] Testando: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                # Verificar se é receita (tem palavras-chave)
                if any(keyword in response.text.lower() for keyword in ['ingredientes', 'preparo', 'modo de fazer']):
                    print(f"✅ Receita encontrada!")
                    
                    drink = scrapper.add_recipe(response.text, "html", url)
                    if drink:
                        total_found += 1
                        print(f"    📝 {drink['titulo']}")
                        if drink['imagem']:
                            print(f"    🖼️ {drink['imagem']}")
                    else:
                        print(f"    ❌ Erro no processamento")
                else:
                    print(f"❌ Não é uma receita")
            else:
                print(f"❌ Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            
        # Delay entre requests
        time.sleep(DELAY_REQUESTS)
    
    print(f"\n🎯 Processamento concluído!")
    print(f"📊 Total encontradas: {total_found} receitas")
    return total_found

def process_single_url(scrapper, url_input):
    """Processar uma URL específica"""
    
    # Se for apenas número, construir URL
    if url_input.isdigit():
        url = f"{BASE_URL}{URL_PATTERN}{url_input}"
    else:
        url = url_input
        
    print(f"\n🔍 Processando: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            drink = scrapper.add_recipe(response.text, "html", url)
            if drink:
                print(f"✅ Receita processada: {drink['titulo']}")
                if drink.get('categoria'):
                    print(f"🍽️ Categoria: {drink['categoria']}")
                print(f"📝 Ingredientes: {len(drink['ingredientes'])}")
                print(f"👨‍🍳 Preparo: {len(drink['modo_preparo'])}")
                if drink['imagem']:
                    print(f"🖼️ Imagem: {drink['imagem']}")
                return True
            else:
                print(f"❌ Falha no processamento")
        else:
            print(f"❌ Status {response.status_code}: Página não encontrada")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        
    return False



def main():
    """Execução automática - sem menu"""
    print("🍹 DrinkSimples Scrapper - Execução Automática")
    print("=" * 60)
    print(f"🌐 Site: {BASE_URL}")
    print(f"📊 Range: {RANGE_INICIO} até {RANGE_FIM}")
    print(f"📁 Imagens: {PASTA_IMAGENS}/")
    print(f"💾 Dados: {PASTA_DADOS}/")
    print("=" * 60)
    
    scrapper = DrinkSimplesScrapper()
    
    print(f"\n🚀 INICIANDO PROCESSAMENTO AUTOMÁTICO...")
    print(f"📊 Processando {RANGE_FIM - RANGE_INICIO + 1} URLs")
    
    # 1. Processar todas as URLs do range
    total_encontradas = process_url_range(scrapper)
    
    if total_encontradas > 0:
        print(f"\n✅ {total_encontradas} receitas processadas!")
        
        # 2. Gerar JSON automaticamente
        print(f"\n💾 Gerando JSON limpo...")
        json_file = scrapper.save_consolidated_json()
        
        # 3. Resumo final
        print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
        print(f"📊 {total_encontradas} receitas coletadas")
        print(f"🖼️ Imagens baixadas: {PASTA_IMAGENS}/")
        print(f"💾 JSON para BD: {json_file}")
        
    else:
        print(f"\n❌ Nenhuma receita encontrada no range {RANGE_INICIO}-{RANGE_FIM}")
        print(f"🔍 Verifique se o range está correto no topo do arquivo")
    
    print(f"\n👋 Scrapping finalizado!")


if __name__ == "__main__":
    main() 