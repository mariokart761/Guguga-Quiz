## 工具功能說明

將阿摩格式的`html`試卷檔案，轉換為`json`格式內容。`json`格式試卷可以提供給後台並存入資料庫。

## 安裝與使用
```
pip install beautifulsoup4
python html2json_parser.py "your_file.html"
python html2json_parser.py "quiz_html" -o "output"
```

## 其他格式轉換

- 若想要使用其他格式的`html`試卷檔案，可提供你的試卷檔案給大模型，生成 python 腳本，批量轉換為範例格式(`output_example.json`)即可。