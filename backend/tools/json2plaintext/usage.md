## 工具功能說明

將`json`格式的試卷檔案，轉換為乾淨文字內容。方便提供給大模型進行試卷內容分析。

## 使用方式
```
python json2plaintext.py ./json_folder ./output
```

## 連同答案一起輸出

```
python json2plaintext.py ./json_folder ./output --include-answers
```