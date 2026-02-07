import pygame
import os
import sys
import math


class VirtualJoystick:
    """Віртуальний джойстик для мобільних пристроїв"""

    def __init__(self, x, y, radius):
        self.center_x = x
        self.center_y = y
        self.radius = radius
        self.handle_radius = radius // 2
        self.handle_x = x
        self.handle_y = y
        self.is_active = False
        self.angle = 0
        self.distance = 0

    def draw(self, screen):
        # Основа джойстика
        pygame.draw.circle(screen, (100, 100, 100, 128),
                           (self.center_x, self.center_y),
                           self.radius)
        pygame.draw.circle(screen, (150, 150, 150, 180),
                           (self.center_x, self.center_y),
                           self.radius, 2)

        # Ручка джойстика
        pygame.draw.circle(screen, (80, 80, 80, 200),
                           (int(self.handle_x), int(self.handle_y)),
                           self.handle_radius)
        pygame.draw.circle(screen, (200, 200, 200, 180),
                           (int(self.handle_x), int(self.handle_y)),
                           self.handle_radius, 2)

    def update(self, touch_pos=None):
        if touch_pos and self.is_active:
            touch_x, touch_y = touch_pos

            # Обмеження ручки в межах джойстика
            dx = touch_x - self.center_x
            dy = touch_y - self.center_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > self.radius:
                dx = dx * self.radius / distance
                dy = dy * self.radius / distance
                distance = self.radius

            self.handle_x = self.center_x + dx
            self.handle_y = self.center_y + dy
            self.distance = distance / self.radius  # Нормалізація від 0 до 1

            # Розрахунок кута для напрямку
            if distance > 10:  # Мертва зона
                self.angle = math.atan2(dy, dx)
            else:
                self.angle = 0
                self.distance = 0
        elif not self.is_active:
            # Повернення ручки в центр
            self.handle_x += (self.center_x - self.handle_x) * 0.3
            self.handle_y += (self.center_y - self.handle_y) * 0.3
            self.distance *= 0.7

    def get_direction(self):
        """Повертає нормалізований вектор руху"""
        if self.distance > 0.1:  # Мертва зона
            return math.cos(self.angle), math.sin(self.angle)
        return 0, 0

    def activate(self, touch_pos):
        touch_x, touch_y = touch_pos
        # Перевірка чи торкнулись джойстика
        dx = touch_x - self.center_x
        dy = touch_y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= self.radius * 1.5:  # Трохи більша зона для зручності
            self.is_active = True
            self.update(touch_pos)
            return True
        return False

    def deactivate(self):
        self.is_active = False


class MobileButton:
    """Віртуальна кнопка для мобільних пристроїв"""

    def __init__(self, x, y, width, height, text, color=(80, 80, 80)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.pressed_color = (color[0] - 30, color[1] - 30, color[2] - 30)
        self.current_color = color
        self.is_pressed = False
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen):
        # Тінь кнопки
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (40, 40, 40, 150), shadow_rect, border_radius=10)

        # Кнопка
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=10)

        # Текст
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_press(self, touch_pos):
        if self.rect.collidepoint(touch_pos):
            self.is_pressed = True
            self.current_color = self.pressed_color
            return True
        return False

    def release(self):
        self.is_pressed = False
        self.current_color = self.color


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        # Отримання розмірів екрану для адаптації
        info = pygame.display.Info()
        self.screen_width = min(800, info.current_w)
        self.screen_height = min(400, info.current_h)

        # Для Android: повноекранний режим
        if hasattr(pygame, 'ANDROID'):
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.screen_width, self.screen_height = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        pygame.display.set_caption("IT Game - Mobile")

        # Шлях до ресурсів
        self.base_path = self.get_base_path()

        # Завантаження та оптимізація ресурсів
        self.load_and_optimize_assets()

        # Мобільні елементи керування
        self.setup_mobile_controls()

        # Ігрові змінні
        self.gameplay = True
        self.player_x = self.screen_width // 4
        self.player_y = self.screen_height - 150
        self.player_speed = 5
        self.is_jump = False
        self.jump_count = 8
        self.player_anim_count = 0
        self.bg_x = 0

        # Оптимізація: менше привидів для мобільних пристроїв
        self.max_ghosts = 3
        self.ghost_list_in_game = []
        self.bullets = []
        self.bullets_left = 8

        # Таймери
        self.ghost_timer = pygame.USEREVENT + 1
        pygame.time.set_timer(self.ghost_timer, 3000)  # Менше привидів

        # Шрифти
        self.setup_fonts()

        # Музика та звуки
        self.load_audio()

        # ФПС лічильник
        self.clock = pygame.time.Clock()
        self.fps = 30
        self.running = True

        # Статистика пам'яті (для налагодження)
        self.ghost_count = 0

    def get_base_path(self):
        """Отримання базового шляху"""
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        elif hasattr(pygame, 'ANDROID'):
            return "/data/data/org.itgame/files/app"
        return os.path.dirname(os.path.abspath(__file__))

    def load_and_optimize_assets(self):
        """Завантаження та оптимізація ресурсів для мобільних пристроїв"""
        try:
            # Оптимізація: конвертація всіх зображень
            def load_and_scale(path, scale_factor=0.7):
                img = pygame.image.load(path).convert_alpha()
                # Зменшення розміру для мобільних пристроїв
                new_width = int(img.get_width() * scale_factor)
                new_height = int(img.get_height() * scale_factor)
                return pygame.transform.smoothscale(img, (new_width, new_height))

            # Фон
            bg_path = os.path.join(self.base_path, "Photos", "Background.jpeg")
            if not os.path.exists(bg_path):
                bg_path = os.path.join(self.base_path, "background.jpg")

            self.bg = pygame.image.load(bg_path).convert()
            # Масштабування фону під розмір екрану
            self.bg = pygame.transform.scale(self.bg, (self.screen_width, self.screen_height))

            # Привид (оптимізований)
            ghost_path = os.path.join(self.base_path, "Photos", "ghost.png")
            self.ghost = load_and_scale(ghost_path, 0.5)  # Зменшений розмір

            # Анімації гравця (оптимізовані)
            self.walk_left = []
            self.walk_right = []

            # Оптимізація: менше кадрів анімації для мобільних пристроїв
            walk_frames = 3

            for i in range(1, walk_frames + 1):
                left_path = os.path.join(self.base_path, "Photos", "left", f"{i}.png")
                right_path = os.path.join(self.base_path, "Photos", "right", f"{i + 3}.png")

                if os.path.exists(left_path):
                    img = load_and_scale(left_path, 0.6)
                    self.walk_left.append(img)
                else:
                    # Запасний варіант: створення простих прямокутників
                    surf = pygame.Surface((30, 50), pygame.SRCALPHA)
                    pygame.draw.rect(surf, (100, 200, 100), (0, 0, 30, 50))
                    self.walk_left.append(surf)

                if os.path.exists(right_path):
                    img = load_and_scale(right_path, 0.6)
                    self.walk_right.append(img)
                else:
                    surf = pygame.Surface((30, 50), pygame.SRCALPHA)
                    pygame.draw.rect(surf, (100, 150, 200), (0, 0, 30, 50))
                    self.walk_right.append(surf)

            # Кулі (оптимізовані)
            bullet_path = os.path.join(self.base_path, "Photos", "bullet.png")
            if os.path.exists(bullet_path):
                self.bullet = load_and_scale(bullet_path, 0.3)
            else:
                # Запасний варіант: проста куля
                self.bullet = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(self.bullet, (255, 0, 0), (4, 4), 4)

            # Іконка
            icon_path = os.path.join(self.base_path, "Photos", "icon.png")
            if os.path.exists(icon_path):
                icon = pygame.image.load(icon_path)
                pygame.display.set_icon(icon)

        except Exception as e:
            print(f"Error loading assets: {e}")
            self.create_fallback_assets()

    def create_fallback_assets(self):
        """Створення простих ресурсів, якщо не вдалося завантажити"""
        # Простий фон
        self.bg = pygame.Surface((self.screen_width, self.screen_height))
        self.bg.fill((50, 50, 80))

        # Простий привид
        self.ghost = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(self.ghost, (200, 200, 200, 180), (20, 20), 20)

        # Прості анімації
        self.walk_left = []
        self.walk_right = []
        for i in range(3):
            surf = pygame.Surface((30, 50), pygame.SRCALPHA)
            color = (100 + i * 20, 200, 100)
            pygame.draw.rect(surf, color, (0, 10, 30, 40))
            self.walk_left.append(surf)
            self.walk_right.append(surf)

    def setup_mobile_controls(self):
        """Налаштування мобільних елементів керування"""
        # Лівий джойстик для руху
        joystick_x = self.screen_width // 6
        joystick_y = self.screen_height - 100
        self.move_joystick = VirtualJoystick(joystick_x, joystick_y, 50)

        # Правий джойстик для пострілу
        shoot_x = self.screen_width - self.screen_width // 6
        shoot_y = self.screen_height - 100
        self.shoot_joystick = VirtualJoystick(shoot_x, shoot_y, 40)

        # Кнопки
        button_width = 80
        button_height = 40
        button_margin = 20

        # Кнопка стрибка
        self.jump_button = MobileButton(
            self.screen_width - button_width - button_margin,
            button_margin,
            button_width,
            button_height,
            "JUMP",
            (0, 150, 0)
        )

        # Кнопка паузи
        self.pause_button = MobileButton(
            button_margin,
            button_margin,
            button_width,
            button_height,
            "PAUSE",
            (150, 150, 0)
        )

        # Кнопка пострілу
        self.shoot_button = MobileButton(
            self.screen_width // 2 - button_width // 2,
            self.screen_height - button_height - button_margin,
            button_width,
            button_height,
            "FIRE",
            (150, 0, 0)
        )

        # Активні тачі
        self.active_touches = {}

    def setup_fonts(self):
        """Налаштування шрифтів"""
        try:
            font_path = os.path.join(self.base_path, "Fonts", "Roboto-Black.ttf")
            if os.path.exists(font_path):
                self.title_font = pygame.font.Font(font_path, 36)
                self.ui_font = pygame.font.Font(font_path, 24)
            else:
                self.title_font = pygame.font.Font(None, 36)
                self.ui_font = pygame.font.Font(None, 24)
        except:
            self.title_font = pygame.font.Font(None, 36)
            self.ui_font = pygame.font.Font(None, 24)

        self.lose_label = self.title_font.render("Game Over!", True, (255, 100, 100))
        self.restart_label = self.ui_font.render("Tap to restart", True, (200, 200, 200))

    def load_audio(self):
        """Завантаження аудіо"""
        try:
            # На Android музика може не працювати, тому обробляємо помилки
            if hasattr(pygame, 'ANDROID'):
                return  # На Android часто проблеми з музикою

            music_path = os.path.join(self.base_path, "Music", "bg.mp3")
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(0.3)  # Типіше для мобільних
                pygame.mixer.music.play(-1)
        except:
            print("Audio not available")

    def handle_touch_events(self):
        """Обробка тач-подій для мобільних пристроїв"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Обробка тач-подій
            elif event.type == pygame.FINGERDOWN:
                touch_id = event.finger_id
                touch_x = event.x * self.screen_width
                touch_y = event.y * self.screen_height

                # Зберігаємо тач
                self.active_touches[touch_id] = (touch_x, touch_y)

                # Перевіряємо елементи керування
                if self.move_joystick.activate((touch_x, touch_y)):
                    continue
                elif self.shoot_joystick.activate((touch_x, touch_y)):
                    continue
                elif self.jump_button.check_press((touch_x, touch_y)):
                    if not self.is_jump:
                        self.is_jump = True
                        self.jump_count = 8
                elif self.shoot_button.check_press((touch_x, touch_y)):
                    self.shoot_bullet()
                elif self.pause_button.check_press((touch_x, touch_y)):
                    self.gameplay = not self.gameplay

            elif event.type == pygame.FINGERMOTION:
                touch_id = event.finger_id
                if touch_id in self.active_touches:
                    touch_x = event.x * self.screen_width
                    touch_y = event.y * self.screen_height
                    self.active_touches[touch_id] = (touch_x, touch_y)

                    # Оновлюємо активні джойстики
                    if self.move_joystick.is_active:
                        self.move_joystick.update((touch_x, touch_y))
                    if self.shoot_joystick.is_active:
                        self.shoot_joystick.update((touch_x, touch_y))

            elif event.type == pygame.FINGERUP:
                touch_id = event.finger_id
                if touch_id in self.active_touches:
                    del self.active_touches[touch_id]

                    # Деактивуємо джойстики
                    self.move_joystick.deactivate()
                    self.shoot_joystick.deactivate()

                    # Відпускаємо кнопки
                    self.jump_button.release()
                    self.shoot_button.release()
                    self.pause_button.release()

            # Клавіатура (для ПК/емулятора)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not self.is_jump:
                    self.is_jump = True
                    self.jump_count = 8
                elif event.key == pygame.K_b and self.bullets_left > 0:
                    self.shoot_bullet()
                elif event.key == pygame.K_p:
                    self.gameplay = not self.gameplay
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

            # Генерація привидів
            elif event.type == self.ghost_timer and self.gameplay:
                if len(self.ghost_list_in_game) < self.max_ghosts:
                    self.ghost_list_in_game.append(
                        self.ghost.get_rect(topleft=(self.screen_width, self.player_y))
                    )
                    self.ghost_count += 1

    def shoot_bullet(self):
        """Постріл кулею"""
        if self.bullets_left > 0:
            # Напрямок пострілу з джойстика
            if self.shoot_joystick.distance > 0.1:
                angle = self.shoot_joystick.angle
                speed_x = math.cos(angle) * 8
                speed_y = math.sin(angle) * 8
            else:
                # Стандартний напрямок
                speed_x = 8
                speed_y = 0

            bullet_rect = self.bullet.get_rect(center=(self.player_x + 30, self.player_y + 15))
            self.bullets.append({
                'rect': bullet_rect,
                'speed_x': speed_x,
                'speed_y': speed_y
            })
            self.bullets_left -= 1

    def update(self):
        """Оновлення ігрової логіки"""
        if not self.gameplay:
            return

        # Рух з джойстика
        move_x, move_y = self.move_joystick.get_direction()
        self.player_x += move_x * self.player_speed
        self.player_y += move_y * self.player_speed * 0.5  # Повільніший вертикальний рух

        # Обмеження гравця на екрані
        self.player_x = max(50, min(self.screen_width - 100, self.player_x))
        self.player_y = max(100, min(self.screen_height - 100, self.player_y))

        # Стрибок
        if self.is_jump:
            if self.jump_count >= -8:
                neg = 1 if self.jump_count > 0 else -1
                self.player_y -= (self.jump_count ** 2) * 0.5 * neg
                self.jump_count -= 1
            else:
                self.is_jump = False
                self.jump_count = 8

        # Оновлення привидів
        for ghost in self.ghost_list_in_game[:]:
            ghost.x -= 5  # Повільніше для мобільних

            # Видалення привидів за екраном
            if ghost.x < -100:
                self.ghost_list_in_game.remove(ghost)
                continue

            # Перевірка зіткнення з гравцем
            player_rect = self.walk_left[0].get_rect(topleft=(self.player_x, self.player_y))
            if player_rect.colliderect(ghost):
                self.gameplay = False

        # Оновлення куль
        for bullet in self.bullets[:]:
            bullet['rect'].x += bullet['speed_x']
            bullet['rect'].y += bullet['speed_y']

            # Видалення куль за екраном
            if (bullet['rect'].x < -50 or bullet['rect'].x > self.screen_width + 50 or
                    bullet['rect'].y < -50 or bullet['rect'].y > self.screen_height + 50):
                self.bullets.remove(bullet)
                continue

            # Перевірка зіткнень з привидами
            for ghost in self.ghost_list_in_game[:]:
                if bullet['rect'].colliderect(ghost):
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    if ghost in self.ghost_list_in_game:
                        self.ghost_list_in_game.remove(ghost)
                    break

        # Оновлення джойстиків
        self.move_joystick.update()
        self.shoot_joystick.update()

        # Анімація
        self.player_anim_count = (self.player_anim_count + 1) % len(self.walk_left)

        # Рух фону
        if abs(move_x) > 0.1:
            self.bg_x -= move_x * 2
            if self.bg_x <= -self.screen_width:
                self.bg_x = 0
            elif self.bg_x >= self.screen_width:
                self.bg_x = 0

    def draw(self):
        """Відображення гри"""
        # Фон
        self.screen.blit(self.bg, (self.bg_x, 0))
        self.screen.blit(self.bg, (self.bg_x + self.screen_width, 0))
        self.screen.blit(self.bg, (self.bg_x - self.screen_width, 0))

        # Привиди
        for ghost in self.ghost_list_in_game:
            self.screen.blit(self.ghost, ghost)

        # Гравець
        if self.move_joystick.distance > 0.1 and math.cos(self.move_joystick.angle) < 0:
            self.screen.blit(self.walk_left[self.player_anim_count], (self.player_x, self.player_y))
        else:
            self.screen.blit(self.walk_right[self.player_anim_count], (self.player_x, self.player_y))

        # Кулі
        for bullet in self.bullets:
            self.screen.blit(self.bullet, bullet['rect'])

        # Мобільні елементи керування (напівпрозорі)
        control_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        # Джойстики
        self.move_joystick.draw(control_surface)
        self.shoot_joystick.draw(control_surface)

        # Кнопки
        self.jump_button.draw(control_surface)
        self.pause_button.draw(control_surface)
        self.shoot_button.draw(control_surface)

        # Написання на кнопках
        ammo_text = self.ui_font.render(f"Ammo: {self.bullets_left}", True, (255, 255, 255))
        control_surface.blit(ammo_text, (self.screen_width // 2 - 50, 10))

        # Ghosts: текст
        ghosts_text = self.ui_font.render(f"Ghosts: {len(self.ghost_list_in_game)}", True, (255, 255, 255))
        control_surface.blit(ghosts_text, (self.screen_width // 2 - 50, 40))

        # FPS
        fps_text = self.ui_font.render(f"FPS: {int(self.clock.get_fps())}", True, (200, 200, 200))
        control_surface.blit(fps_text, (10, self.screen_height - 30))

        # Накладання елементів керування
        self.screen.blit(control_surface, (0, 0))

        # Екран програшу
        if not self.gameplay:
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            self.screen.blit(self.lose_label,
                             (self.screen_width // 2 - self.lose_label.get_width() // 2,
                              self.screen_height // 2 - 50))
            self.screen.blit(self.restart_label,
                             (self.screen_width // 2 - self.restart_label.get_width() // 2,
                              self.screen_height // 2 + 20))

            # Статистика
            stats = [
                f"Ghosts defeated: {self.ghost_count}",
                f"Bullets used: {8 - self.bullets_left}",
                "Tap anywhere to restart"
            ]

            for i, stat in enumerate(stats):
                stat_text = self.ui_font.render(stat, True, (200, 200, 200))
                self.screen.blit(stat_text,
                                 (self.screen_width // 2 - stat_text.get_width() // 2,
                                  self.screen_height // 2 + 60 + i * 30))

    def restart_game(self):
        """Перезапуск гри"""
        self.gameplay = True
        self.player_x = self.screen_width // 4
        self.player_y = self.screen_height - 150
        self.ghost_list_in_game.clear()
        self.bullets.clear()
        self.bullets_left = 8
        self.is_jump = False
        self.jump_count = 8
        self.bg_x = 0

        # Скидання джойстиків
        self.move_joystick.deactivate()
        self.shoot_joystick.deactivate()

    def run(self):
        """Головний ігровий цикл"""
        while self.running:
            self.handle_touch_events()

            # Рестарт при тапі на екрані програшу
            if not self.gameplay and pygame.mouse.get_pressed()[0]:
                mouse_pos = pygame.mouse.get_pos()
                self.restart_game()

            self.update()
            self.draw()

            pygame.display.flip()
            self.clock.tick(self.fps)

            # Автоматичне зменшення FPS при низькій продуктивності
            current_fps = self.clock.get_fps()
            if current_fps < 25 and self.fps > 20:
                self.fps = max(20, self.fps - 5)
            elif current_fps > 35 and self.fps < 60:
                self.fps = min(60, self.fps + 5)

        pygame.quit()
        sys.exit()


# Оптимізація для Android
if hasattr(pygame, 'ANDROID'):
    # На Android важливо викликати ці функції
    import android
    import android.mixer as mixer


    def android_init():
        """Ініціалізація для Android"""
        # Встановлення орієнтації
        android.init()
        android.map_key(android.KEYCODE_BACK, pygame.K_ESCAPE)

        # Налаштування аудіо
        try:
            mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except:
            pass

if __name__ == "__main__":
    # Запуск гри
    try:
        if hasattr(pygame, 'ANDROID'):
            android_init()

        game = Game()
        game.run()
    except Exception as e:
        # Запис помилки для налагодження
        error_file = os.path.join(os.path.dirname(__file__), "error_log.txt")
        with open(error_file, "w") as f:
            f.write(str(e))
        print(f"Error occurred: {e}")
        pygame.quit()