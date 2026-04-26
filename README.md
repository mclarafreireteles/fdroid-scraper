# F-Droid Scraper

## Instalação

```
pip install pyyaml
```

## Uso básico

```
python fdroid_react_native_scraper.py
```

### Outras opções
#### Também gera JSON
```
python fdroid_react_native_scraper.py --json
```

#### Já tem o repo clonado, não quer clonar de novo
```
python fdroid_react_native_scraper.py --no-clone
```

#### Nome customizado para o CSV
```
python fdroid_react_native_scraper.py --output minha_pesquisa.csv
```

#### Forçar re-clone do zero
```
python fdroid_react_native_scraper.py --force-clone
```

## Funcionamento
1. Clona o repositório fdroiddata do GitHub usando --sparse + --depth=1 (só baixa a pasta metadata/, sem o histórico todo)
2. Varre todos os ~5.800 arquivos .yml buscando os padrões react-native, @react-native, com.facebook.react, etc.
3. Extrai de cada app: app_id, nome, licença, categorias, website, link do código-fonte, versões disponíveis e o trecho exato do YAML onde aparece a evidência do React Native
4. Salva em CSV (e opcionalmente JSON) e imprime um resumo no terminal com distribuição por categoria
