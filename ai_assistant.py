import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import queue
import time
from datetime import datetime
import tensorflow as tf
import torch
from transformers import AutoTokenizer, AutoModel, pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class AIAssistant:
    def __init__(self):
        self.config_file = Path("config/ai_assistant.json")
        self.config = self.load_config()
        self.command_history: List[Dict] = []
        self.message_queue = queue.Queue()
        self.processing_thread = None
        self.running = True
        
        # Initialize AI models
        self.initialize_models()
        
        # Start processing thread
        self.start_processing()
    
    def load_config(self) -> dict:
        """Load AI assistant configuration"""
        default_config = {
            "models": {
                "command": "microsoft/DialoGPT-medium",
                "analysis": "bert-base-uncased",
                "sentiment": "distilbert-base-uncased-finetuned-sst-2-english"
            },
            "processing": {
                "max_length": 128,
                "min_confidence": 0.7,
                "batch_size": 16
            },
            "features": {
                "command_processing": True,
                "sentiment_analysis": True,
                "predictive_maintenance": True,
                "context_help": True
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            logging.error(f"Error loading AI assistant config: {e}")
            return default_config
    
    def save_config(self):
        """Save AI assistant configuration"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving AI assistant config: {e}")
    
    def initialize_models(self):
        """Initialize AI models"""
        try:
            # Initialize command processing model
            self.command_tokenizer = AutoTokenizer.from_pretrained(
                self.config["models"]["command"]
            )
            self.command_model = AutoModel.from_pretrained(
                self.config["models"]["command"]
            )
            
            # Initialize analysis model
            self.analysis_tokenizer = AutoTokenizer.from_pretrained(
                self.config["models"]["analysis"]
            )
            self.analysis_model = AutoModel.from_pretrained(
                self.config["models"]["analysis"]
            )
            
            # Initialize sentiment analysis pipeline
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model=self.config["models"]["sentiment"]
            )
            
            # Initialize TF-IDF vectorizer for command matching
            self.vectorizer = TfidfVectorizer()
            self.command_vectors = None
            
            logging.info("AI models initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing AI models: {e}")
            raise
    
    def start_processing(self):
        """Start message processing thread"""
        def process_messages():
            while self.running:
                try:
                    if not self.message_queue.empty():
                        message = self.message_queue.get()
                        self.process_message(message)
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Error processing messages: {e}")
        
        self.processing_thread = threading.Thread(target=process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        """Stop message processing"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()
    
    def process_message(self, message: Dict):
        """Process incoming message"""
        try:
            message_type = message.get("type", "unknown")
            content = message.get("content", "")
            
            if message_type == "command":
                response = self.process_command(content)
            elif message_type == "query":
                response = self.process_query(content)
            elif message_type == "analysis":
                response = self.analyze_system_state(content)
            else:
                response = {"error": "Unknown message type"}
            
            # Store in command history
            self.command_history.append({
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "response": response
            })
            
            return response
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return {"error": str(e)}
    
    def process_command(self, command: str) -> Dict:
        """Process natural language command"""
        try:
            # Tokenize command
            inputs = self.command_tokenizer(
                command,
                return_tensors="pt",
                max_length=self.config["processing"]["max_length"],
                truncation=True
            )
            
            # Get command embedding
            with torch.no_grad():
                outputs = self.command_model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1)
            
            # Match command to known commands
            command_vector = self.vectorizer.transform([command])
            if self.command_vectors is not None:
                similarities = (command_vector * self.command_vectors.T).A[0]
                best_match_idx = similarities.argmax()
                confidence = similarities[best_match_idx]
                
                if confidence >= self.config["processing"]["min_confidence"]:
                    return {
                        "command": command,
                        "matched": True,
                        "confidence": float(confidence),
                        "action": self.get_command_action(best_match_idx)
                    }
            
            # No match found
            return {
                "command": command,
                "matched": False,
                "confidence": 0.0,
                "suggestion": self.get_command_suggestion(command)
            }
            
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return {"error": str(e)}
    
    def process_query(self, query: str) -> Dict:
        """Process help query"""
        try:
            # Analyze query intent
            inputs = self.analysis_tokenizer(
                query,
                return_tensors="pt",
                max_length=self.config["processing"]["max_length"],
                truncation=True
            )
            
            with torch.no_grad():
                outputs = self.analysis_model(**inputs)
                query_embedding = outputs.last_hidden_state.mean(dim=1)
            
            # Get sentiment
            sentiment = self.sentiment_analyzer(query)[0]
            
            # Generate context-aware response
            response = self.generate_help_response(
                query,
                query_embedding,
                sentiment["label"]
            )
            
            return {
                "query": query,
                "sentiment": sentiment,
                "response": response
            }
            
        except Exception as e:
            logging.error(f"Error processing query: {e}")
            return {"error": str(e)}
    
    def analyze_system_state(self, state_data: Dict) -> Dict:
        """Analyze system state and provide recommendations"""
        try:
            # Convert state data to feature vector
            features = self.extract_state_features(state_data)
            
            # Analyze performance metrics
            performance_analysis = self.analyze_performance(features)
            
            # Analyze security metrics
            security_analysis = self.analyze_security(features)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(
                performance_analysis,
                security_analysis
            )
            
            return {
                "timestamp": datetime.now().isoformat(),
                "performance": performance_analysis,
                "security": security_analysis,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logging.error(f"Error analyzing system state: {e}")
            return {"error": str(e)}
    
    def extract_state_features(self, state_data: Dict) -> np.ndarray:
        """Extract relevant features from system state data"""
        features = []
        try:
            # CPU metrics
            features.extend([
                state_data.get("cpu", {}).get("usage", 0),
                state_data.get("cpu", {}).get("temperature", 0),
                state_data.get("cpu", {}).get("frequency", 0)
            ])
            
            # Memory metrics
            features.extend([
                state_data.get("memory", {}).get("usage", 0),
                state_data.get("memory", {}).get("available", 0)
            ])
            
            # Disk metrics
            features.extend([
                state_data.get("disk", {}).get("usage", 0),
                state_data.get("disk", {}).get("read_speed", 0),
                state_data.get("disk", {}).get("write_speed", 0)
            ])
            
            # Network metrics
            features.extend([
                state_data.get("network", {}).get("bandwidth", 0),
                state_data.get("network", {}).get("latency", 0)
            ])
            
            return np.array(features)
            
        except Exception as e:
            logging.error(f"Error extracting state features: {e}")
            return np.zeros(10)  # Return zero vector on error
    
    def analyze_performance(self, features: np.ndarray) -> Dict:
        """Analyze system performance metrics"""
        try:
            # Simple threshold-based analysis
            cpu_score = self._calculate_score(features[0], [70, 85])
            memory_score = self._calculate_score(features[3], [75, 90])
            disk_score = self._calculate_score(features[6], [80, 95])
            network_score = self._calculate_score(features[8], [60, 80])
            
            return {
                "cpu": {
                    "score": cpu_score,
                    "status": self._get_status(cpu_score)
                },
                "memory": {
                    "score": memory_score,
                    "status": self._get_status(memory_score)
                },
                "disk": {
                    "score": disk_score,
                    "status": self._get_status(disk_score)
                },
                "network": {
                    "score": network_score,
                    "status": self._get_status(network_score)
                }
            }
            
        except Exception as e:
            logging.error(f"Error analyzing performance: {e}")
            return {}
    
    def analyze_security(self, features: np.ndarray) -> Dict:
        """Analyze system security metrics"""
        try:
            # Analyze security-related features
            # This is a placeholder for more sophisticated security analysis
            return {
                "threat_level": "low",
                "vulnerabilities": [],
                "recommendations": [
                    "Regular security updates",
                    "Enable firewall",
                    "Use strong passwords"
                ]
            }
            
        except Exception as e:
            logging.error(f"Error analyzing security: {e}")
            return {}
    
    def generate_recommendations(
        self,
        performance: Dict,
        security: Dict
    ) -> List[Dict]:
        """Generate system recommendations"""
        recommendations = []
        
        try:
            # Performance recommendations
            for component, data in performance.items():
                if data.get("status") == "warning":
                    recommendations.append({
                        "type": "performance",
                        "component": component,
                        "priority": "medium",
                        "action": f"Optimize {component} usage"
                    })
                elif data.get("status") == "critical":
                    recommendations.append({
                        "type": "performance",
                        "component": component,
                        "priority": "high",
                        "action": f"Immediate {component} optimization required"
                    })
            
            # Security recommendations
            if security.get("threat_level") in ["medium", "high"]:
                recommendations.append({
                    "type": "security",
                    "priority": "high",
                    "action": "Review security settings"
                })
            
            return recommendations
            
        except Exception as e:
            logging.error(f"Error generating recommendations: {e}")
            return []
    
    def _calculate_score(self, value: float, thresholds: List[float]) -> float:
        """Calculate component score based on thresholds"""
        try:
            if value <= thresholds[0]:
                return 1.0
            elif value <= thresholds[1]:
                return 1.0 - (value - thresholds[0]) / (thresholds[1] - thresholds[0])
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _get_status(self, score: float) -> str:
        """Get status based on score"""
        if score >= 0.8:
            return "good"
        elif score >= 0.5:
            return "warning"
        else:
            return "critical"
    
    def get_command_suggestion(self, command: str) -> str:
        """Get suggestion for unrecognized command"""
        return "Could not recognize command. Try using simpler terms or check documentation."
    
    def get_command_action(self, command_idx: int) -> Dict:
        """Get action for recognized command"""
        # Placeholder for command action mapping
        return {"type": "system", "action": "unknown"}
