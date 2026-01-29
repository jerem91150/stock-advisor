"""
Tests pour le module de détection hardware.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hardware.detector import (
    HardwareDetector, GPUType, GPUInfo, SystemInfo, LLMRecommendation
)


class TestGPUInfo:
    """Tests pour la structure GPUInfo."""

    def test_create_nvidia_gpu(self):
        """Test création info GPU NVIDIA."""
        gpu = GPUInfo(
            gpu_type=GPUType.NVIDIA,
            name="NVIDIA GeForce RTX 4090",
            vram_gb=24.0,
            driver_version="535.98",
            cuda_version="12.2"
        )

        assert gpu.gpu_type == GPUType.NVIDIA
        assert gpu.name == "NVIDIA GeForce RTX 4090"
        assert gpu.vram_gb == 24.0
        assert gpu.cuda_version == "12.2"

    def test_create_amd_gpu(self):
        """Test création info GPU AMD."""
        gpu = GPUInfo(
            gpu_type=GPUType.AMD,
            name="AMD Radeon RX 7900 XTX",
            vram_gb=24.0
        )

        assert gpu.gpu_type == GPUType.AMD
        assert gpu.cuda_version is None


class TestSystemInfo:
    """Tests pour la structure SystemInfo."""

    def test_create_system_info_with_gpu(self):
        """Test création info système avec GPU."""
        gpu = GPUInfo(
            gpu_type=GPUType.NVIDIA,
            name="RTX 4090",
            vram_gb=24.0
        )
        system = SystemInfo(
            os="Windows 11",
            cpu_name="Intel Core i9",
            cpu_cores=8,
            ram_gb=32.0,
            gpu=gpu
        )

        assert system.gpu is not None
        assert system.gpu.vram_gb == 24.0

    def test_create_system_info_without_gpu(self):
        """Test création info système sans GPU."""
        system = SystemInfo(
            os="Linux",
            cpu_name="AMD Ryzen",
            cpu_cores=16,
            ram_gb=64.0,
            gpu=None
        )

        assert system.gpu is None


class TestLLMRecommendation:
    """Tests pour la structure LLMRecommendation."""

    def test_create_recommendation(self):
        """Test création recommandation LLM."""
        rec = LLMRecommendation(
            model_name="llama3.1:8b",
            model_size="8B paramètres",
            quantization="FP16",
            ollama_command="ollama pull llama3.1:8b",
            reason="Test reason"
        )

        assert "llama" in rec.model_name
        assert "ollama pull" in rec.ollama_command


class TestHardwareDetector:
    """Tests pour la classe HardwareDetector."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test."""
        self.detector = HardwareDetector()

    # Tests de détection NVIDIA

    @patch('subprocess.run')
    def test_detect_nvidia_gpu_success(self, mock_run):
        """Test détection GPU NVIDIA réussie."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NVIDIA GeForce RTX 4090, 24564, 535.98\nCUDA Version: 12.2"
        )

        gpu = self.detector.detect_nvidia_gpu()

        assert gpu is not None
        assert gpu.gpu_type == GPUType.NVIDIA
        assert "RTX 4090" in gpu.name
        assert gpu.vram_gb > 20  # ~24 GB

    @patch('subprocess.run')
    def test_detect_nvidia_gpu_not_found(self, mock_run):
        """Test détection GPU NVIDIA non trouvé."""
        mock_run.side_effect = FileNotFoundError()

        gpu = self.detector.detect_nvidia_gpu()

        assert gpu is None

    @patch('subprocess.run')
    def test_detect_nvidia_gpu_error(self, mock_run):
        """Test détection GPU NVIDIA avec erreur."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        gpu = self.detector.detect_nvidia_gpu()

        assert gpu is None

    # Tests de recommandation LLM

    def test_recommend_llm_high_vram(self):
        """Test recommandation pour GPU haute VRAM (24GB+)."""
        gpu = GPUInfo(GPUType.NVIDIA, "RTX 4090", 24.0)
        system = SystemInfo("Windows", "CPU", 8, 32.0, gpu)

        rec = self.detector.recommend_llm(system)

        # Devrait recommander un gros modèle
        assert "70b" in rec.model_name.lower() or "8x7b" in rec.model_name.lower()

    def test_recommend_llm_medium_vram(self):
        """Test recommandation pour GPU VRAM moyenne (8-16GB)."""
        gpu = GPUInfo(GPUType.NVIDIA, "RTX 3080", 10.0)
        system = SystemInfo("Windows", "CPU", 8, 32.0, gpu)

        rec = self.detector.recommend_llm(system)

        # Devrait recommander un modèle 8B quantifié
        assert "8b" in rec.model_name.lower()

    def test_recommend_llm_low_vram(self):
        """Test recommandation pour GPU faible VRAM (4-6GB)."""
        gpu = GPUInfo(GPUType.NVIDIA, "GTX 1650", 4.0)
        system = SystemInfo("Windows", "CPU", 4, 16.0, gpu)

        rec = self.detector.recommend_llm(system)

        # Devrait recommander un petit modèle
        assert "phi" in rec.model_name.lower() or "3b" in rec.model_name.lower() or "mini" in rec.model_name.lower()

    def test_recommend_llm_no_gpu(self):
        """Test recommandation sans GPU (CPU only)."""
        system = SystemInfo("Linux", "AMD Ryzen", 8, 32.0, None)

        rec = self.detector.recommend_llm(system)

        # Devrait recommander un modèle léger pour CPU
        assert "CPU" in rec.reason or "phi" in rec.model_name.lower()

    def test_recommend_llm_16gb_vram(self):
        """Test recommandation pour 16GB VRAM."""
        gpu = GPUInfo(GPUType.NVIDIA, "RTX 4080", 16.0)
        system = SystemInfo("Windows", "CPU", 8, 32.0, gpu)

        rec = self.detector.recommend_llm(system)

        # Devrait recommander 8B full precision
        assert "8b" in rec.model_name.lower()
        assert "FP16" in rec.quantization or "full" in rec.quantization.lower()

    # Tests de vérification Ollama

    @patch('subprocess.run')
    def test_check_ollama_installed_yes(self, mock_run):
        """Test Ollama installé."""
        mock_run.return_value = MagicMock(returncode=0)

        assert self.detector.check_ollama_installed()

    @patch('subprocess.run')
    def test_check_ollama_installed_no(self, mock_run):
        """Test Ollama non installé."""
        mock_run.side_effect = FileNotFoundError()

        assert not self.detector.check_ollama_installed()

    @patch('subprocess.run')
    def test_get_ollama_models(self, mock_run):
        """Test liste des modèles Ollama."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NAME\nllama3.1:8b\nmistral:7b\nphi3:mini"
        )

        models = self.detector.get_ollama_models()

        assert len(models) == 3
        assert "llama3.1:8b" in models

    @patch('subprocess.run')
    def test_get_ollama_models_empty(self, mock_run):
        """Test liste modèles Ollama vide."""
        mock_run.return_value = MagicMock(returncode=0, stdout="NAME\n")

        models = self.detector.get_ollama_models()

        assert len(models) == 0

    # Tests de détection système

    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_count')
    @patch('platform.processor')
    @patch('platform.system')
    @patch('platform.release')
    def test_detect_system_basic(
        self, mock_release, mock_system, mock_processor,
        mock_cpu_count, mock_memory
    ):
        """Test détection système de base."""
        mock_system.return_value = "Windows"
        mock_release.return_value = "10"
        mock_processor.return_value = "Intel Core i7"
        mock_cpu_count.return_value = 8
        mock_memory.return_value = MagicMock(total=32 * 1024**3)

        # Mock la détection GPU
        with patch.object(self.detector, 'detect_nvidia_gpu', return_value=None):
            with patch.object(self.detector, 'detect_amd_gpu', return_value=None):
                with patch.object(self.detector, 'detect_intel_gpu', return_value=None):
                    system = self.detector.detect_system()

        assert system is not None
        assert "Windows" in system.os
        assert system.cpu_cores == 8
        assert system.ram_gb > 30  # ~32 GB

    # Tests du rapport

    def test_generate_report(self):
        """Test génération du rapport."""
        gpu = GPUInfo(GPUType.NVIDIA, "RTX 4090", 24.0, "535.98", "12.2")
        self.detector.system_info = SystemInfo(
            "Windows 11",
            "Intel Core i9",
            8,
            32.0,
            gpu
        )

        with patch.object(self.detector, 'check_ollama_installed', return_value=True):
            with patch.object(self.detector, 'get_ollama_models', return_value=["llama3.1:8b"]):
                report = self.detector.generate_report()

        assert "RAPPORT HARDWARE" in report
        assert "RTX 4090" in report
        assert "24.0" in report  # VRAM
        assert "NVIDIA" in report
        assert "OLLAMA" in report
        assert "llama3.1:8b" in report


class TestGPUType:
    """Tests pour l'enum GPUType."""

    def test_gpu_types(self):
        """Test des types de GPU."""
        assert GPUType.NVIDIA.value == "nvidia"
        assert GPUType.AMD.value == "amd"
        assert GPUType.INTEL.value == "intel"
        assert GPUType.CPU_ONLY.value == "cpu"
