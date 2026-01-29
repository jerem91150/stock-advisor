"""
Détection Hardware - GPU/VRAM et recommandation de modèle LLM
"""

import subprocess
import platform
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import psutil
from loguru import logger


class GPUType(Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    CPU_ONLY = "cpu"


@dataclass
class GPUInfo:
    """Informations sur le GPU détecté."""
    gpu_type: GPUType
    name: str
    vram_gb: float
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None


@dataclass
class SystemInfo:
    """Informations système complètes."""
    os: str
    cpu_name: str
    cpu_cores: int
    ram_gb: float
    gpu: Optional[GPUInfo]


@dataclass
class LLMRecommendation:
    """Recommandation de modèle LLM basée sur le hardware."""
    model_name: str
    model_size: str
    quantization: str
    ollama_command: str
    reason: str


class HardwareDetector:
    """Détecteur de hardware pour optimiser la configuration LLM."""

    def __init__(self):
        self.system_info: Optional[SystemInfo] = None

    def detect_nvidia_gpu(self) -> Optional[GPUInfo]:
        """Détecte un GPU NVIDIA via nvidia-smi."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    parts = lines[0].split(', ')
                    if len(parts) >= 3:
                        name = parts[0].strip()
                        vram_mb = float(parts[1].strip())
                        driver = parts[2].strip()

                        # Détecter version CUDA
                        cuda_version = self._get_cuda_version()

                        return GPUInfo(
                            gpu_type=GPUType.NVIDIA,
                            name=name,
                            vram_gb=vram_mb / 1024,
                            driver_version=driver,
                            cuda_version=cuda_version
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"NVIDIA GPU non détecté: {e}")
        return None

    def _get_cuda_version(self) -> Optional[str]:
        """Récupère la version CUDA installée."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extraire version CUDA depuis nvidia-smi
                result2 = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "CUDA Version:" in result2.stdout:
                    for line in result2.stdout.split('\n'):
                        if "CUDA Version:" in line:
                            parts = line.split("CUDA Version:")
                            if len(parts) > 1:
                                return parts[1].strip().split()[0]
        except Exception:
            pass
        return None

    def detect_amd_gpu(self) -> Optional[GPUInfo]:
        """Détecte un GPU AMD via rocm-smi (Linux) ou via WMI (Windows)."""
        if platform.system() == "Linux":
            return self._detect_amd_linux()
        elif platform.system() == "Windows":
            return self._detect_amd_windows()
        return None

    def _detect_amd_linux(self) -> Optional[GPUInfo]:
        """Détecte GPU AMD sur Linux via rocm-smi."""
        try:
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parser la sortie rocm-smi
                vram_gb = 0.0
                for line in result.stdout.split('\n'):
                    if "Total Memory" in line:
                        # Extraire la valeur en bytes et convertir
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.isdigit():
                                vram_gb = int(part) / (1024**3)
                                break

                # Obtenir le nom du GPU
                result_name = subprocess.run(
                    ["rocm-smi", "--showproductname"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                name = "AMD GPU"
                if result_name.returncode == 0:
                    for line in result_name.stdout.split('\n'):
                        if "Card series" in line:
                            name = line.split(':')[-1].strip()
                            break

                return GPUInfo(
                    gpu_type=GPUType.AMD,
                    name=name,
                    vram_gb=vram_gb
                )
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"AMD GPU non détecté (Linux): {e}")
        return None

    def _detect_amd_windows(self) -> Optional[GPUInfo]:
        """Détecte GPU AMD sur Windows via WMI."""
        try:
            import wmi
            c = wmi.WMI()
            for gpu in c.Win32_VideoController():
                if "AMD" in gpu.Name or "Radeon" in gpu.Name:
                    vram_bytes = gpu.AdapterRAM if gpu.AdapterRAM else 0
                    # AdapterRAM peut être négatif sur certains systèmes (overflow 32-bit)
                    if vram_bytes < 0:
                        vram_bytes = 0
                    return GPUInfo(
                        gpu_type=GPUType.AMD,
                        name=gpu.Name,
                        vram_gb=vram_bytes / (1024**3)
                    )
        except ImportError:
            logger.debug("Module WMI non disponible pour détection AMD")
        except Exception as e:
            logger.debug(f"AMD GPU non détecté (Windows): {e}")
        return None

    def detect_intel_gpu(self) -> Optional[GPUInfo]:
        """Détecte un GPU Intel intégré."""
        if platform.system() == "Windows":
            try:
                import wmi
                c = wmi.WMI()
                for gpu in c.Win32_VideoController():
                    if "Intel" in gpu.Name:
                        vram_bytes = gpu.AdapterRAM if gpu.AdapterRAM else 0
                        if vram_bytes < 0:
                            vram_bytes = 0
                        return GPUInfo(
                            gpu_type=GPUType.INTEL,
                            name=gpu.Name,
                            vram_gb=vram_bytes / (1024**3)
                        )
            except Exception as e:
                logger.debug(f"Intel GPU non détecté: {e}")
        return None

    def detect_system(self) -> SystemInfo:
        """Détecte les informations système complètes."""
        # CPU info
        cpu_name = platform.processor() or "Unknown CPU"
        cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 1

        # RAM
        ram_bytes = psutil.virtual_memory().total
        ram_gb = ram_bytes / (1024**3)

        # GPU - essayer dans l'ordre de préférence
        gpu = self.detect_nvidia_gpu()
        if not gpu:
            gpu = self.detect_amd_gpu()
        if not gpu:
            gpu = self.detect_intel_gpu()

        self.system_info = SystemInfo(
            os=f"{platform.system()} {platform.release()}",
            cpu_name=cpu_name,
            cpu_cores=cpu_cores,
            ram_gb=ram_gb,
            gpu=gpu
        )

        return self.system_info

    def recommend_llm(self, system_info: Optional[SystemInfo] = None) -> LLMRecommendation:
        """
        Recommande un modèle LLM adapté au hardware détecté.

        Règles de recommandation basées sur la VRAM disponible:
        - >= 24GB: llama3.1:70b-instruct-q4_K_M ou mixtral:8x7b
        - >= 16GB: llama3.1:8b ou mistral:7b (full precision)
        - >= 8GB: llama3.1:8b-instruct-q4_K_M ou mistral:7b-instruct-q4_K_M
        - >= 6GB: llama3.2:3b ou phi3:mini
        - >= 4GB: llama3.2:1b ou phi3:mini-q4
        - < 4GB ou CPU: phi3:mini (CPU mode) ou tinyllama
        """
        if system_info is None:
            system_info = self.system_info or self.detect_system()

        vram_gb = 0.0
        is_gpu = False

        if system_info.gpu and system_info.gpu.gpu_type != GPUType.CPU_ONLY:
            vram_gb = system_info.gpu.vram_gb
            is_gpu = True

        # Règles de recommandation
        if vram_gb >= 24:
            return LLMRecommendation(
                model_name="llama3.1:70b-instruct-q4_K_M",
                model_size="70B paramètres",
                quantization="Q4_K_M (4-bit)",
                ollama_command="ollama pull llama3.1:70b-instruct-q4_K_M",
                reason=f"Votre GPU ({system_info.gpu.name}) avec {vram_gb:.1f}GB VRAM permet d'utiliser les plus grands modèles."
            )
        elif vram_gb >= 16:
            return LLMRecommendation(
                model_name="llama3.1:8b",
                model_size="8B paramètres",
                quantization="FP16 (full precision)",
                ollama_command="ollama pull llama3.1:8b",
                reason=f"Votre GPU ({system_info.gpu.name}) avec {vram_gb:.1f}GB VRAM permet d'utiliser Llama 3.1 8B en pleine précision."
            )
        elif vram_gb >= 8:
            return LLMRecommendation(
                model_name="llama3.1:8b-instruct-q4_K_M",
                model_size="8B paramètres",
                quantization="Q4_K_M (4-bit)",
                ollama_command="ollama pull llama3.1:8b-instruct-q4_K_M",
                reason=f"Votre GPU ({system_info.gpu.name}) avec {vram_gb:.1f}GB VRAM permet d'utiliser Llama 3.1 8B quantifié."
            )
        elif vram_gb >= 6:
            return LLMRecommendation(
                model_name="llama3.2:3b",
                model_size="3B paramètres",
                quantization="FP16",
                ollama_command="ollama pull llama3.2:3b",
                reason=f"Votre GPU ({system_info.gpu.name}) avec {vram_gb:.1f}GB VRAM est adapté à Llama 3.2 3B."
            )
        elif vram_gb >= 4:
            return LLMRecommendation(
                model_name="phi3:mini",
                model_size="3.8B paramètres",
                quantization="Q4_K_M",
                ollama_command="ollama pull phi3:mini",
                reason=f"Votre GPU avec {vram_gb:.1f}GB VRAM est limité. Phi-3 Mini est recommandé."
            )
        else:
            # CPU mode ou très faible VRAM
            return LLMRecommendation(
                model_name="phi3:mini",
                model_size="3.8B paramètres",
                quantization="Q4_K_M (CPU mode)",
                ollama_command="ollama pull phi3:mini",
                reason=f"Pas de GPU compatible détecté ou VRAM insuffisante. Phi-3 Mini fonctionnera en mode CPU avec {system_info.ram_gb:.1f}GB RAM."
            )

    def check_ollama_installed(self) -> bool:
        """Vérifie si Ollama est installé."""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_ollama_models(self) -> list[str]:
        """Liste les modèles Ollama installés."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                models = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
                return models
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def generate_report(self) -> str:
        """Génère un rapport complet sur le hardware et les recommandations."""
        if not self.system_info:
            self.detect_system()

        info = self.system_info
        recommendation = self.recommend_llm()
        ollama_installed = self.check_ollama_installed()
        ollama_models = self.get_ollama_models() if ollama_installed else []

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    RAPPORT HARDWARE - STOCK ADVISOR              ║
╠══════════════════════════════════════════════════════════════════╣
║ SYSTÈME                                                          ║
╠══════════════════════════════════════════════════════════════════╣
  OS: {info.os}
  CPU: {info.cpu_name}
  Cœurs: {info.cpu_cores}
  RAM: {info.ram_gb:.1f} GB

╠══════════════════════════════════════════════════════════════════╣
║ GPU                                                              ║
╠══════════════════════════════════════════════════════════════════╣
"""
        if info.gpu:
            report += f"""  Type: {info.gpu.gpu_type.value.upper()}
  Modèle: {info.gpu.name}
  VRAM: {info.gpu.vram_gb:.1f} GB
"""
            if info.gpu.driver_version:
                report += f"  Driver: {info.gpu.driver_version}\n"
            if info.gpu.cuda_version:
                report += f"  CUDA: {info.gpu.cuda_version}\n"
        else:
            report += "  Aucun GPU compatible détecté (mode CPU)\n"

        report += f"""
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMANDATION LLM                                               ║
╠══════════════════════════════════════════════════════════════════╣
  Modèle: {recommendation.model_name}
  Taille: {recommendation.model_size}
  Quantification: {recommendation.quantization}

  {recommendation.reason}

  Pour installer:
  $ {recommendation.ollama_command}

╠══════════════════════════════════════════════════════════════════╣
║ OLLAMA                                                           ║
╠══════════════════════════════════════════════════════════════════╣
  Installé: {"✓ Oui" if ollama_installed else "✗ Non"}
"""
        if ollama_models:
            report += f"  Modèles disponibles: {', '.join(ollama_models)}\n"
        elif ollama_installed:
            report += "  Aucun modèle installé\n"

        report += """
╚══════════════════════════════════════════════════════════════════╝
"""
        return report


def main():
    """Point d'entrée pour test standalone."""
    detector = HardwareDetector()
    detector.detect_system()
    print(detector.generate_report())


if __name__ == "__main__":
    main()
