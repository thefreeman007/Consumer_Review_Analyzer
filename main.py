import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import matplotlib.pyplot as plt

def summarize_and_classify_reviews(input_text, model, tokenizer, max_new_tokens=128):
    """
    Generate classification based on input text.
    根据输入文本生成分类。
    :param input_text: The review text to be classified
    :param input_text: 要分类的评论文本
    :param model: The preloaded model
    :param model: 预加载的模型
    :param tokenizer: The preloaded tokenizer
    :param tokenizer: 预加载的tokenizer
    :param max_new_tokens: The maximum number of tokens to generate
    :param max_new_tokens: 生成的最大token数
    :return: Return the classification result
    :return: 返回分类结果
    """
    # Tokenizing input text and moving to the device (GPU or CPU)
    # 对输入文本进行分词并移动到设备（GPU或CPU）
    input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

    # Generate output from the model
    # 生成输出
    outputs = model.generate(**input_ids,
                             max_new_tokens=max_new_tokens,  # Control the length of the output  # 控制输出长度
                             temperature=0.7,  # Add some randomness to increase output diversity  # 增加一定的随机性，提高生成多样性
                             top_p=0.6,  # Use nucleus sampling to control output quality  # 使用 nucleus sampling，控制输出的质量
                             top_k=50,  # Limit the sampling range to avoid irrelevant outputs  # 通过限制可能的采样范围，避免无效输出
                             num_beams=5,  # Use beam search to optimize generation results  # 使用束搜索来优化生成结果
                             eos_token_id=tokenizer.eos_token_id,  # Define the end-of-sequence token  # 定义终止标志
                             pad_token_id=tokenizer.pad_token_id  # Define the padding token ID  # 填充token id

                             )

    # Decode the generated text
    # 解码生成的文本
    result_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return result_text.strip()


def extract_category(result_text, category_reasons):
    """
    Extract and return the category.
    提取并返回分类。
    :param result_text: The classification result returned by the model
    :param result_text: 模型返回的分类结果
    :param category_reasons: The current list of category reasons
    :param category_reasons: 当前已有的分类原因
    :return: Category
    :return: 分类
    """
    # Directly extract the category from the model output, only return the first line
    # 直接返回模型输出的分类，只返回第一行
    if "Category:" in result_text:
        # Extract content after the last "Category:" and only return the first line
        # 获取最后一个的 "Category:" 后面的内容，并仅返回第一行
        category_text = result_text.split("Category:")[-1].strip()
        category_text = category_text.split('\n')[0].strip()

        # Remove all asterisks (if present)
        # 去除所有星号（如果有的话）
        category_text = category_text.replace('*', '').strip()

        # If the category text is empty, set it to 'Others'
        # 如果分类文本为空，设置为 'Others'
        if category_text == '':
            category_text = 'Others'
        elif category_text not in category_reasons:
            # If the category text is non-empty and not in the existing reasons list, append it
            # 如果分类文本非空且不在分类原因列表中，添加到列表
            print('update reasons')
            category_reasons.append(category_text)

        return category_text, category_reasons  # Return category and updated reasons
        # 返回分类和更新后的分类原因

    # If the result text is empty, directly return 'Others'
    # 如果结果文本为空，直接返回 'Others'
    if result_text.strip() == '':
        category_text = 'Others'
        return category_text, category_reasons


def process_reviews(csv_file, column_name, model, tokenizer):
    """
    Read reviews from a CSV file and classify them.
    从CSV文件中读取评论并进行分类。
    :param csv_file: The path to the CSV file
    :param csv_file: CSV文件路径
    :param column_name: The name of the column containing the reviews
    :param column_name: 评论所在的列名
    :param model: The preloaded model
    :param model: 加载好的模型
    :param tokenizer: The preloaded tokenizer
    :param tokenizer: 加载好的tokenizer
    :return: Return the classification result for each review
    :return: 返回每条评论的分类结果
    """
    # Note: Some CSV files may not be read correctly
    # 注意个别csv可能无法读取
    df = pd.read_csv(csv_file, encoding='GBK')

    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in CSV.")
        # 检查CSV文件是否包含指定的列 / Check if the CSV file contains the specified column

    results = []
    category_reasons = [
        'Customer Service',   # 客户服务 / Customer Service
        'Quality Problem',     # 质量问题 / Quality Problem
        'Delivery',            # 配送 / Delivery
        'Price',               # 价格 / Price
        'Personal Preference', # 个人偏好 / Personal Preference
        'Not Worth It',        # 不值得购买 / Not Worth It
        'Others'               # 其他 / Others
    ]
    for idx, row in df.iterrows():
        review_text = row[column_name]

        # Improved task prompt to ensure the model clearly outputs the category
        # 改进的任务提示，确保模型清晰输出分类
        task_prompt = f'''
Here is a consumer review after purchasing the product:
"{review_text}"
Please read the following negative consumer review carefully and try to identify the issue the consumer is raising.
Your task is to **summarize** the reason for the dissatisfaction in your own words, explaining why the consumer is unhappy.
If the issue doesn't clearly belong to one of the following categories:
{category_reasons},
please summarize a new reason for the issue.
If you are unable to summarize the reason clearly, just respond with "Others".

Please follow this exact format:

Reason: [Your reason here]
Category: [Your category here]

For example
Review: "I don’t like the color and feel of the product. It's just not what I imagined."
Reason: The product didn’t meet my personal preferences.
Category: Personal Preference
        '''
        result_text = summarize_and_classify_reviews(task_prompt, model, tokenizer)
        # Remove the task prompt and retain only the answer part
        # 去掉任务提示，保留答案部分
        result_text = re.sub(re.escape(task_prompt), "", result_text).strip()
        print('The Answer:', result_text)
        # Extract the category
        # 提取分类
        category, category_reasons = extract_category(result_text, category_reasons)
        print(category,category_reasons)
        results.append({
            "Review": review_text,
            "Category": category
        })

    return results


# Example: Run the function and print results
# 示例：运行函数并打印结果
if __name__ == "__main__":
    # Replace with your file path
    # 请替换为你自己的文件路径
    csv_file = "data/review_data.csv"

    # Replace with the column name where reviews are stored
    # 请替换为评论所在的列名
    column_name = "review"

    # Set the number of CPU threads and cache directory
    # 设置CPU核心数和缓存目录
    torch.set_num_threads(12)

    # model_path
    # 模型路径
    model_path = "J:/my_models/gemma2_9b"

    # Load the model and tokenizer
    # 加载模型和tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        # Auto-allocate devices
        # 自动分配设备
        device_map="auto",
        # you can choose ： bfloat16(for tpu) or float16(gpu more fast),
        # 精度选择进行高效推理
        torch_dtype=torch.float16 ,
    )

    # Process reviews and get categories
    # 处理评论并获得分类
    results = process_reviews(csv_file, column_name, model, tokenizer)

    # Save results to a CSV file containing only reviews and categories
    # 保存结果到CSV文件，仅包含评论和分类

    results_df = pd.DataFrame(results)
    # Print the results for inspection
    # 打印结果以供检查
    print(results_df)
    results_df.to_csv("data/result_data.csv", index=False)

    # Count the number of occurrences in each category
    # 统计各分类的数量
    category_counts = results_df['Category'].value_counts()

    # Plot a pie chart
    # 绘制饼图
    plt.figure(figsize=(8, 8))
    category_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, cmap='rainbow', legend=False,labels=category_counts.index)

    # Add a title
    # 添加标题
    plt.title('Distribution of Categories in Consumer Reviews')
    # 确保没有图例，避免出现 'count' 显示

    # Display the pie chart
    # 显示饼图
    plt.axis('equal')  # Make the pie chart circular
    plt.show()
