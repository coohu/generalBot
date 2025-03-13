from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from pymilvus import MilvusClient, connections, Collection
from typing import List, Dict, Any
from pprint import pprint
from tqdm import tqdm
from glob import glob
import model as md
import json
import env 

collection_name = "my_rag_collection"
milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus", db_name="default")
# milvus_client.load_collection(collection_name, 1)
# connections.connect("default", host="localhost", port="19530")
# collection = Collection(collection_name)
# collection.load()
# print(collection, '===============')

def get_max_id(collection_name):
    results = milvus_client.query(
        collection_name=collection_name,
        output_fields=["id"],
        limit=1,
        sort=f"id desc"  # 按ID降序排序
    )
    return results[0]['id'] if results else 0

def collection_count(collection):
    try:
        num_entities = collection.num_entities
        # result = collection.query(expr="", output_fields=["count(*)"])
        # count = result[0]["count(*)"]
        return num_entities
    except Exception as e:
        print(f"错误：{e}")
        return None

def add(path="./data/*.md", separator="\n"):
    text_lines = []
    for file_path in glob(path, recursive=False):
        with open(file_path, "r", encoding='utf-8') as file:
            file_text = file.read()
        text_lines += file_text.split(separator)

    text_lines = [item for item in text_lines if len(item) >= 3]

    print('add().len(text_lines): ', len(text_lines))
    entities = md.bgem3(text_lines[:100])
    # for i in range(0, len(text_lines), 10):
    #     be = bge_m3_ef(text_lines[i:i + 10])
    #     entities += be["dense"]
    embedding_dim = len(entities[0])
    # if milvus_client.has_collection(collection_name):
    #     milvus_client.drop_collection(collection_name)
    if not milvus_client.has_collection(collection_name):
        milvus_client.create_collection(
            collection_name=collection_name,
            dimension=embedding_dim,
            metric_type="IP",  # Inner product distance
            consistency_level="Strong",  # Strong consistency level
        )
    n = get_max_id(collection_name)
    data = []
    for i, v in enumerate(entities):
        data.append({"id": i+n, "vector": v, "text": text_lines[i]})
    # for i, line in enumerate(tqdm(text_lines, desc="Creating embeddings")):
    #     data.append({"id": i, "vector": emb_text(line), "text": line})
    milvus_client.insert(collection_name=collection_name, data=data)

# add()
# exit()
def copy_collection(new_collection_name, ef, *args):
    data = milvus_client.query(
        collection_name=collection_name,
        filter="",
        output_fields=["text"],
        limit=16384,
    )

    vector_dim = len(  ef(data[0]['text'], *args) )
    print(f'{new_collection_name} vector_dim : ', vector_dim)

    if milvus_client.has_collection(new_collection_name):
        milvus_client.drop_collection(new_collection_name)

    milvus_client.create_collection(
        collection_name=new_collection_name, 
        dimension=vector_dim, 
        metric_type="IP",  # Inner product distance
        consistency_level="Strong",  # Strong consistency level
    )

    cols = []
    for idx, doc in enumerate(data):
        record = {
            "id": idx,
            "vector": ef(doc['text'], *args),
            "text": doc['text']
        }
        cols.append(record)

    milvus_client.insert(collection_name=new_collection_name, data=cols)
    # milvus_client.create_index(collection_name=new_collection_name, index_type="AUTOINDEX")

# copy_collection('collection_doubao', md.ssy)
# copy_collection('collection_text_v3', md.ssy, 'text-embedding-v3')
# copy_collection('collection_dmeta', md.ollama)

def query(col_name=None, ef=md.bgem3, *args):
    def query_collection(cn ,kws, embed_func, *embed_name):
        search_res = milvus_client.search(
            collection_name=cn,
            data= [embed_func(kws, *embed_name)],
            limit=10,  # Return top 3 results
            search_params={"metric_type": "IP", "params": {}},  # Inner product distance
            output_fields=["text", "id"],  # Return the text field
        )
        retrieved_lines_with_distances = [
            # (res["entity"]["id"], res["distance"], res["entity"]["text"]) for res in search_res[0]
            res["entity"]["text"] for res in search_res[0]
        ]
        for it in retrieved_lines_with_distances:
            pprint(it)
        print('-----------------------------------------------------------------------------------------------------')

    while True:
        question = input("请输入搜索内容：")
        if question == "":
            break
        if col_name:
            query_collection(col_name, question, ef, *args)
        else:
            for ebd in env.model['embed']:
                match ebd:
                    case 'Doubao-embedding':
                        query_collection(
                            env.collection_names[ebd], 
                            question,
                            md.ssy, 
                            ebd,
                        )
                    case 'text-embedding-v3':
                        query_collection(
                            env.collection_names[ebd], 
                            question,
                            md.ssy, 
                            ebd,
                        )
                    case 'shaw/dmeta-embedding-zh':
                        query_collection(
                            env.collection_names[ebd], 
                            question,
                            md.ollama, 
                            ebd,
                        )
                    case 'BAAI/bge-m3':
                        query_collection(
                            env.collection_names[ebd], 
                            question,
                            md.bgem3,
                        )

# query()
#query(collection_name)
#query('collection_doubao', md.ssy)
#query('collection_text_v3', md.ssy)
#query('collection_dmeta', md.ollama)

def collections_schema():
    collections = milvus_client.list_collections()
    
    print(f"总共 {len(collections)} 个集合:")
    for collection_name in collections:
        print(f"\n集合: {collection_name}")
        collection_info = milvus_client.describe_collection(collection_name)
        
        print("集合信息:")
        for key, value in collection_info.items():
            print(f"  {key}: {value}")
        
        try:
            sample_record = milvus_client.query(
                collection_name=collection_name, 
                output_fields=["*"],
                limit=1
            )
            
            if sample_record:
                print("\n字段示例:")
                for key, value in sample_record[0].items():
                    print(f"  {key}: {type(value).__name__}")
        except Exception as e:
            print(f"  无法获取字段详情: {e}")


def rm(coll_name):
    if milvus_client.has_collection(coll_name):
        milvus_client.drop_collection(coll_name)

# rm(collection_name) 
# rm('collection_dmeta') 
# rm('collection_doubao') 
# rm('collection_text_v3') 
# rm('collection_test') 
# collections_schema()

def article_graph(file_path):
    with open(file_path, "r", encoding='utf-8') as file:
        file_text = file.read()
    prompt = ['''
按以下要求处理这篇文章
1、为整篇文章分片，要求尽量保持分片内句子表达意思的完整性，但每个分片不超过100个字。
2、每个分片的结束处用 { } 做标记。
3、{ } 内部填写该分片的关键词。分片的关键词为该分片中出现的专有名词。例如：人名，地名，国家名，组织或公司的名字等。
4、按以上要求标注文章的内容后，完整的输出文件内容和你添加的分片标记，不要添加评论或其他内容。
5、除了插入分片标记和关键词，不要修改或删除原文件内容。
''',
 "从这篇文章中提取5个关键词，不需要其他内容。"]

    system_prompt = f"你是一个文档处理助手。需要严格按照要求处理用户给你的文档。\n用户的文档是:\n{file_text}"

    def ssy(ocmd):
        for idx, ppw in enumerate(prompt) :
            messages = [
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content":ppw},
            ]
            if idx == 0:
                print('\n\n', ocmd , "知识图谱")
            else:
                print('\n\n', ocmd , "关键词提取")
            response = md.chat.create(
                model = ocmd, 
                messages = messages,
                temperature = 0,
                stream = True
            )
            # res = response.choices[0].message.content
            # messages.append({"role": "assistant", "content": res})
            for chunk in response:
                if chunk.choices[0].delta and chunk.choices[0].delta.content: 
                    print(chunk.choices[0].delta.content, end="", flush=True)  

    for ocmd in env.model['chat'][1:]:
         for idx, ppw in enumerate(prompt) :
            messages = [
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content":ppw},
            ]
            if idx == 0:
                print('\n\n', ocmd , "知识图谱")
            else:
                print('\n\n', ocmd , "关键词提取")

            md.ochat(messages, ocmd)

    # for ocmd in ['MiniMax-Text-01','abab6.5s-chat','qwen-turbo']:
    #     ssy(ocmd)

article_graph('./data/art.short.txt')


