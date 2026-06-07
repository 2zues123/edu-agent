# 高校教务教学智能体

面向高校教务咨询、培养方案查询、课程学习答疑和办事流程引导的 Agent 应用原型。

## 知识库构建

项目使用 `conda` 的 `langchain` 环境运行脚本和 Agent。

安装依赖：

```bash
pip install -r requirements.txt
```

生成知识库切分结果：

```bash
conda run -n langchain python scripts/build_chunks.py
```

生成本地 FAISS 向量索引：

```bash
conda run -n langchain python scripts/build_vector_index.py
```

默认使用 `sentence-transformers` 的 `BAAI/bge-small-zh-v1.5` 生成中文语义向量。也可以切换后端：

```bash
conda run -n langchain python scripts/build_vector_index.py --embedding-backend hashing
conda run -n langchain python scripts/build_vector_index.py --embedding-backend api --embedding-model text-embedding-3-small
```

输出文件：

```text
data/processed/chunks.jsonl
data/processed/build_report.json
data/index/faiss/chunks.faiss
data/index/faiss/metadata.jsonl
data/index/faiss/index_config.json
```

当前脚本支持解析 `.doc`、`.docx`、`.pdf`、`.txt` 和 `.md` 文件，并按文档类别、标题、来源文件和章节标题生成可检索的知识片段。
检索层会读取 `index_config.json`，使用与建库一致的 embedding 后端查询 FAISS，并融合关键词检索结果；如果索引不存在，会自动回退到关键词检索。

## LangGraph Agent

命令行测试：

```bash
conda run -n langchain python main.py "机器学习课程多少学分？"
```

只检索依据、不调用大模型：

```bash
conda run -n langchain python main.py --no-llm "机器学习课程多少学分？"
```

## Streamlit 演示界面

启动 Web 演示：

```bash
conda run -n langchain streamlit run app.py
```

侧边栏可以切换是否调用大模型，也可以调整检索片段数量。关闭大模型时，页面只展示检索依据，适合快速验证知识库命中情况。
