"""
Motor de animación para crear videos infantiles
"""
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random
from typing import Tuple, List
from config import Config

# Configurar logging
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class Animator:
    """Generador de animaciones y efectos visuales"""
    
    def __init__(self):
        self.width = Config.VIDEO_WIDTH
        self.height = Config.VIDEO_HEIGHT
        self.bg_color = Config.BACKGROUND_COLOR
        self.primary_color = Config.PRIMARY_COLOR
        self.secondary_color = Config.SECONDARY_COLOR
        self.frames_dir = Config.TEMP_DIR / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        
    def create_title_frame(self, title: str) -> Path:
        """
        Crea un frame con el título del video
        
        Args:
            title: Título del video
            
        Returns:
            Path: Ruta del frame creado
        """
        logger.info(f"Creando frame de título: '{title}'")
        
        try:
            # Crear imagen
            img = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Intentar usar una fuente personalizada, si falla usar default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            except:
                font = ImageFont.load_default()
                small_font = font
            
            # Dibujar fondo con gradiente (simulado con rectángulos)
            self._draw_gradient_background(draw)
            
            # Dibujar título
            title_y = self.height // 3
            bbox = draw.textbbox((0, 0), title, font=font)
            text_width = bbox[2] - bbox[0]
            title_x = (self.width - text_width) // 2
            
            draw.text((title_x, title_y), title, fill=self.primary_color, font=font)
            
            # Dibujar decoración
            self._draw_decorations(draw)
            
            # Guardar frame
            frame_path = self.frames_dir / "title_frame.png"
            img.save(frame_path)
            
            logger.info(f"✅ Frame de título creado: {frame_path}")
            return frame_path
            
        except Exception as e:
            logger.error(f"❌ Error creando frame de título: {e}")
            raise
    
    def create_scene_frame(self, scene_description: str, frame_num: int) -> Path:
        """
        Crea un frame para una escena
        
        Args:
            scene_description: Descripción de la escena
            frame_num: Número del frame
            
        Returns:
            Path: Ruta del frame creado
        """
        logger.info(f"Creando frame de escena {frame_num}...")
        
        try:
            # Crear imagen base
            img = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Dibujar fondo
            self._draw_gradient_background(draw)
            
            # Dibujar elementos geométricos coloridos
            self._draw_geometric_shapes(draw, frame_num)
            
            # Dibujar texto de descripción
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            except:
                font = ImageFont.load_default()
            
            text_y = self.height - 100
            bbox = draw.textbbox((0, 0), scene_description[:50], font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (self.width - text_width) // 2
            
            draw.text((text_x, text_y), scene_description[:50], fill=self.primary_color, font=font)
            
            # Guardar frame
            frame_path = self.frames_dir / f"scene_{frame_num:03d}.png"
            img.save(frame_path)
            
            logger.info(f"✅ Frame de escena creado: {frame_path}")
            return frame_path
            
        except Exception as e:
            logger.error(f"❌ Error creando frame de escena: {e}")
            raise
    
    def create_end_frame(self, message: str = "¡Fin!") -> Path:
        """
        Crea un frame de cierre
        
        Args:
            message: Mensaje de despedida
            
        Returns:
            Path: Ruta del frame creado
        """
        logger.info("Creando frame de cierre...")
        
        try:
            img = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Fondo con gradiente
            self._draw_gradient_background(draw)
            
            # Dibujar corazones y decoraciones
            self._draw_hearts(draw)
            
            # Mensaje
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 100)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), message, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            y = self.height // 2 - 50
            
            draw.text((x, y), message, fill=self.primary_color, font=font)
            
            frame_path = self.frames_dir / "end_frame.png"
            img.save(frame_path)
            
            logger.info(f"✅ Frame de cierre creado: {frame_path}")
            return frame_path
            
        except Exception as e:
            logger.error(f"❌ Error creando frame de cierre: {e}")
            raise
    
    def _draw_gradient_background(self, draw: ImageDraw.ImageDraw):
        """Dibuja un fondo gradiente"""
        for y in range(self.height):
            ratio = y / self.height
            r = int(self.bg_color[0] * (1 - ratio) + self.primary_color[0] * ratio)
            g = int(self.bg_color[1] * (1 - ratio) + self.primary_color[1] * ratio)
            b = int(self.bg_color[2] * (1 - ratio) + self.primary_color[2] * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
    
    def _draw_geometric_shapes(self, draw: ImageDraw.ImageDraw, seed: int):
        """Dibuja formas geométricas coloridas"""
        random.seed(seed)
        
        for _ in range(5):
            x = random.randint(50, self.width - 50)
            y = random.randint(50, self.height // 2)
            size = random.randint(30, 100)
            color = (
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            )
            shape_type = random.choice(['circle', 'rect'])
            
            if shape_type == 'circle':
                draw.ellipse([x, y, x + size, y + size], fill=color, outline=self.primary_color)
            else:
                draw.rectangle([x, y, x + size, y + size], fill=color, outline=self.primary_color)
    
    def _draw_decorations(self, draw: ImageDraw.ImageDraw):
        """Dibuja decoraciones especiales"""
        # Estrellas
        star_positions = [(100, 100), (self.width - 100, 100), (100, self.height - 100)]
        for x, y in star_positions:
            self._draw_star(draw, x, y, 30, self.secondary_color)
    
    def _draw_hearts(self, draw: ImageDraw.ImageDraw):
        """Dibuja corazones"""
        heart_positions = [(150, 150), (self.width - 150, 150), (self.width // 2, self.height - 200)]
        for x, y in heart_positions:
            self._draw_heart(draw, x, y, 50, self.primary_color)
    
    def _draw_star(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: Tuple):
        """Dibuja una estrella"""
        points = []
        for i in range(10):
            angle = i * 36 * 3.14159 / 180
            if i % 2 == 0:
                r = size
            else:
                r = size // 2
            px = x + r * __import__('math').cos(angle)
            py = y + r * __import__('math').sin(angle)
            points.append((px, py))
        draw.polygon(points, fill=color, outline=color)
    
    def _draw_heart(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: Tuple):
        """Dibuja un corazón simple"""
        # Simplificado: dos círculos en la parte superior
        draw.ellipse([x - size, y - size, x, y], fill=color, outline=color)
        draw.ellipse([x, y - size, x + size, y], fill=color, outline=color)
        # Base del corazón
        draw.polygon([
            (x - size, y),
            (x + size, y),
            (x, y + size)
        ], fill=color, outline=color)
    
    def get_frames_list(self) -> List[Path]:
        """Retorna lista de todos los frames generados"""
        frames = sorted(self.frames_dir.glob("*.png"))
        logger.info(f"Total de frames disponibles: {len(frames)}")
        return frames


if __name__ == "__main__":
    animator = Animator()
    
    # Test
    title_frame = animator.create_title_frame("Mi Historia Infantil")
    scene_frame = animator.create_scene_frame("Una aventura mágica", 1)
    end_frame = animator.create_end_frame("¡Fin!")
    
    print(f"✅ Frames creados correctamente")
