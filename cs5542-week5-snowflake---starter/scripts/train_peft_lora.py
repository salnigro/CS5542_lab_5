import os
import argparse
import json
import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer

def load_dataset_from_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    
    # Format according to instruction format
    formatted_data = {
        "text": []
    }
    
    for item in data:
        text = f"Instruction:\n{item['instruction']}\n\nInput:\n{item['input']}\n\nOutput:\n{item['output']}"
        formatted_data["text"].append(text)
        
    return Dataset.from_dict(formatted_data)

def main(args):
    print(f"Loading dataset from {args.dataset_path}")
    dataset = load_dataset_from_json(args.dataset_path)
    
    print(f"Loading base model: {args.model_name}")
    # 4-bit quantization config (QLoRA)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto"
    )
    model.config.use_cache = False
    
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    # PEFT Config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "v_proj"]
    )
    
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    
    print("Ready to train. Model architecture:")
    model.print_trainable_parameters()
    
    # Training Arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        save_steps=100,
        logging_steps=10,
        learning_rate=2e-4,
        max_grad_norm=0.3,
        max_steps=args.max_steps,
        warmup_ratio=0.03,
        lr_scheduler_type="constant",
    )
    
    # SFT Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=512,
        tokenizer=tokenizer,
        args=training_args,
    )
    
    print("Starting fine-tuning...")
    trainer.train()
    
    print(f"Saving fine-tuned model to {args.output_dir}")
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Training complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="TinyLlama/TinyLlama-1.1B-Chat-v1.0", help="Base model identifier from HuggingFace")
    parser.add_argument("--dataset_path", type=str, default="data/domain_instructions.json", help="Path to instruction JSON")
    parser.add_argument("--output_dir", type=str, default="models/domain-adapter", help="Where to save the LoRA adapter")
    parser.add_argument("--max_steps", type=int, default=100, help="Number of training steps")
    args = parser.parse_args()
    
    # Create output dir if not exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    main(args)
