#!/usr/bin/env python
import os
import random
import math
from typing import List

# import basic pygame modules
import pygame as pg

# see if we can load more than standard BMP
if not pg.image.get_extended():
    raise SystemExit("Sorry, extended image module required")

# game constants
MAX_SHOTS = 10  # most player bullets onscreen
MAX_BOMBS = 10
SCREENRECT = pg.Rect(0, 0, 640, 480)
PLAYER_SCORE = 0
ALIEN_SCORE = 0
MAX_ITEMS_ON_SCREEN = 4 #最大(n-1)つまで画面にitemを表示可能
ITEM_SPAWN_INTERVAL = random.randint(5000, 20000)


main_dir = os.path.split(os.path.abspath(__file__))[0]


def load_image(file):
    """loads an image, prepares it for play"""
    file = os.path.join(main_dir, "data", file)
    try:
        surface = pg.image.load(file)
    except pg.error:
        raise SystemExit(f'Could not load image "{file}" {pg.get_error()}')
    return surface.convert()


def load_sound(file):
    """because pygame can be compiled without mixer."""
    if not pg.mixer:
        return None
    file = os.path.join(main_dir, "data", file)
    try:
        sound = pg.mixer.Sound(file)
        return sound
    except pg.error:
        print(f"Warning, unable to load, {file}")
    return None


class Gauge(pg.sprite.Sprite):
    """
    ゲージを管理して表示するクラス
    """

    def __init__(self, position, *groups):
        super().__init__(*groups)
        self.image = pg.Surface((50, 100))
        self.image.fill((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.topleft = position
        self.capacity = 10  # ゲージの最大容量
        self.current_value = 0  # 現在のゲージの量
        self.fill_color = (0, 255, 0)  # ゲージの満タン時の色
        self.empty_color = (255, 0, 0)  # ゲージの空の時の色
        self.last_update = pg.time.get_ticks()  # 前回ゲージが更新された時間
        self.font = pg.font.Font(None, 25)  # 数字表示用のフォント

    def update(self):
        """
        ゲージの値に応じて描画を更新する
        """
        # 現在のゲージの量に応じて、ゲージの長さを計算する
        gauge_length = int(self.current_value / self.capacity * self.rect.height)
        fill_rect = pg.Rect(0, self.rect.height - gauge_length, self.rect.width, gauge_length)
        # ゲージを描画する
        self.image.fill(self.empty_color)
        pg.draw.rect(self.image, self.fill_color, fill_rect)
        # 数字でゲージの量を表示する
        text = self.font.render(str(self.current_value), True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.rect.width // 2, self.rect.height // 2))
        self.image.blit(text, text_rect)

    def increase(self):
        """
        2秒ごとにゲージを2増やす
        """
        now = pg.time.get_ticks()
        if now - self.last_update > 2000:  # 2秒経過したら
            self.last_update = now
            self.current_value += 1
            if self.current_value > self.capacity:
                self.current_value = self.capacity

    def can_fire(self):
        """
        ゲージが2以上なら発射可能
        """
        return self.current_value >= 2
    
    def spread_can_fire(self):
        """
        ゲージが4以上なら発射可能
        """
        return self.current_value >= 4
    
    def speed_can_fire(self):
        """
        ゲージが8以上なら発射可能
        """
        return self.current_value >= 8
    
    def get_current_value(self):
        """
        現在のゲージの値を返す
        """
        return self.current_value


class Player(pg.sprite.Sprite):
    """
    Playerのイニシャライザ
    動作メソッド、
    銃の発射位置メソッドを生成しているクラス
    """

    speed = 1
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=SCREENRECT.midbottom)
        self.reloading = 0
        self.origtop = self.rect.top
        self.facing = -1
        self.gauge = Gauge((0, SCREENRECT.height - 100), *groups)  # プレイヤーのゲージ

    def move(self, direction):
        if direction:
            self.facing = direction
        self.rect.move_ip(direction * self.speed, 0)
        self.rect = self.rect.clamp(SCREENRECT)
        if direction < 0:
            self.image = self.images[0]
        elif direction > 0:
            self.image = self.images[1]

    def gunpos(self):
        pos = self.facing * self.gun_offset + self.rect.centerx
        return pos, self.rect.top
   
class Alien(pg.sprite.Sprite):
    """
    エイリアンのイニシャライザ
    動作メソッド
    銃の発射位置メソッド
    エイリアンの位置更新メソッドを生成しているクラス
    """

    speed = 1
    gun_offset = 0
    images: List[pg.Surface] = []

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.reloading = 0
        self.rect = self.image.get_rect(midtop=SCREENRECT.midtop)
        self.facing = -1
        self.origbottom = self.rect.bottom
        self.gauge = Gauge((0, 0), *groups)  # エイリアンのゲージ
        
    def move(self, direction):
        if direction:
            self.facing = direction
        self.rect.move_ip(direction * self.speed, 0)
        self.rect = self.rect.clamp(SCREENRECT)
        if direction < 0:
            self.image = self.images[0]
        elif direction > 0:
            self.image = self.images[1]
    
    def gunpos(self):
        pos = self.rect.centerx
        return pos, self.rect.bottom

    def update(self):
        #self.rect.move_ip(self.facing, 0)
        if not SCREENRECT.contains(self.rect):
            self.facing = -self.facing
            self.rect = self.rect.clamp(SCREENRECT)
            

class Explosion(pg.sprite.Sprite):
    """
    オブジェクトが衝突した際に爆発する演出を作成するクラス
    """

    defaultlife = 12
    animcycle = 3
    images: List[pg.Surface] = []

    def __init__(self, actor, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(center=actor.rect.center)
        self.life = self.defaultlife

    def update(self):
        """
        called every time around the game loop.

        Show the explosion surface for 'defaultlife'.
        Every game tick(update), we decrease the 'life'.

        Also we animate the explosion.
        """
        self.life = self.life - 1
        self.image = self.images[self.life // self.animcycle % 2]
        if self.life <= 0:
            self.kill()


class Shot(pg.sprite.Sprite):
    """
    Playerが使う銃を生成するクラス
    """

    speed = -3
    images: List[pg.Surface] = []

    def __init__(self, pos, angle=0, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.image.set_colorkey((255, 255, 255))  # 背景を透明に設定
        self.rect = self.image.get_rect(midbottom=pos)
        self.mask = pg.mask.from_surface(self.image)  # マスクを作成して透明部分を除外
        self.angle = angle
        
    def __init__(self, pos, angle=0, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=pos)
        self.angle = angle

    def update(self):
        """
        called every time around the game loop.

        Every tick we move the shot upwards.
        """
        dx = self.speed * math.sin(math.radians(self.angle))
        dy = self.speed * math.cos(math.radians(self.angle))
        self.rect.move_ip(dx, dy)
        if self.rect.top <= 0 or self.rect.left <= 0 or self.rect.right >= SCREENRECT.width or self.rect.bottom >= SCREENRECT.height:
            self.kill()
    
    def spread_shot(pos, shots_group, all_sprites_group, spread=5, count=3):
        start_angle = -spread * (count - 1) / 2
        for i in range(count):
            angle = start_angle + spread * i
            shot = Shot(pos, angle)
            shots_group.add(shot)
            all_sprites_group.add(shot)

class Speed_shot(Shot):
    speed = -15
    def __init__(self, pos, *groups):
        super().__init__(pos, *groups)
        

class Bomb(pg.sprite.Sprite):
    """
    Alienが落とす爆弾を生成するクラス
    """

    speed = 3
    images: List[pg.Surface] = []

    def __init__(self, alien_pos, bomb_angle=0, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midtop=alien_pos)
        self.bomb_angle = bomb_angle
        
    def update(self):
        """
        - make an explosion.
        - remove the Bomb.
        """
        dx = self.speed * math.sin(math.radians(self.bomb_angle))
        dy = self.speed * math.cos(math.radians(self.bomb_angle))
        self.rect.move_ip(dx, dy)
        if self.rect.top <= 0 or self.rect.left <= 0 or self.rect.right >= SCREENRECT.width or self.rect.bottom >= SCREENRECT.height:
            self.kill()
    
    def spread_bomb(pos, bombs_group, all_sprites_group, spread=5, count=3):
        start_angle = -spread * (count - 1) / 2
        for i in range(count):
            angle = start_angle + spread * i
            bomb = Bomb(pos, angle)
            bombs_group.add(bomb)
            all_sprites_group.add(bomb)


class Speed_bomb(Bomb):
    speed = 15
    def __init__(self, pos, *groups):
        super().__init__(pos, *groups)

        
class PlayerScore(pg.sprite.Sprite):
    """
    状況に応じて増減し、playerのScoreに関与するスコアクラス
    """

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.font = pg.font.Font(None, 20)
        self.font.set_italic(1)
        self.color ="white"
        self.lastscore = -1
        self.update()
        self.rect = self.image.get_rect().move(500, 450)

    def update(self):
        """We only update the score in update() when it has changed."""
        global PLAYER_SCORE
        if PLAYER_SCORE != self.lastscore:
            self.lastscore = PLAYER_SCORE
            msg = f"Player Score: {PLAYER_SCORE}"
            self.image = self.font.render(msg, 0, self.color)


class AlienScore(pg.sprite.Sprite):
    """
    状況に応じて増減し、AlienのScore関与するスコアクラス
    """

    def __init__(self, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.font = pg.font.Font(None, 20)
        self.font.set_italic(1)
        self.color ="white"
        self.lastscore = -1
        self.update()
        self.rect = self.image.get_rect().move(500, 20)

    def update(self):
        """We only update the score in update() when it has changed."""
        global ALIEN_SCORE
        if ALIEN_SCORE != self.lastscore:
            self.lastscore = ALIEN_SCORE
            msg = f"Alien Score: {ALIEN_SCORE}"
            self.image = self.font.render(msg, 0, self.color)
            
            
class Item(pg.sprite.Sprite):
    """
    ゲーム内でアイテムを表現するクラス。
    speed : int : アイテムの移動速度。
    images : List[pg.Surface] : アイテムを表現する画像のリスト。
    rect : pg.Rect : アイテムの位置とサイズを表す矩形。
    spawned : bool : アイテムが生成されたかどうかを示すフラグ。
    メソッド:
    update():アイテムの位置を更新し、画面端との衝突を処理する。
    spawn():アイテムを画面の中央に生成する。
    is_spawned() -> bool:アイテムが現在生成されているかどうかを確認する。
    collide_bombs(bombs: pg.sprite.Group) -> bool:爆弾との衝突を確認し、処理する。
    collide_shots(shots: pg.sprite.Group) -> bool:ショットとの衝突を確認し、処理する。
    reset():アイテムを初期状態にリセットする。
    """
    
    images: List[pg.Surface] = []#itemの画像リスト

    def __init__(self, *groups: pg.sprite.AbstractGroup) -> None:
        """
        Itemオブジェクトを初期化する。
        引数: *groups : pg.sprite.AbstractGroup : スプライトが所属するグループ。
        """
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = pg.transform.scale(self.images[0], (64, 48))  # 画像サイズを変更
        self.image.set_colorkey((255, 255, 255))  # 背景を透明に設定
        self.rect = self.image.get_rect(center=SCREENRECT.center)  # 矩形を取得
        self.mask = pg.mask.from_surface(self.image)  # マスクを作成して透明部分を除外
        self.rect.topleft = (-100, -100)  # 初期位置を画面外に設定
        self.speed = random.uniform(1.0, 3.0)
        self.spawned = False  # アイテムが生成されたかどうかのフラグ

    def update(self) -> None:
        """
        アイテムの位置を更新し、画面端との衝突を処理する。
        """
        if self.spawned:
            self.rect.move_ip(self.speed, 0)  # アイテムを移動
            if self.rect.right > SCREENRECT.right:
                self.rect.right = SCREENRECT.right  # 右端に合わせる
                self.speed = -self.speed  # 移動方向を反転
            if self.rect.left < 0:
                self.rect.left = 0  # 左端に合わせる
                self.speed = -self.speed  # 移動方向を反転
            if self.rect.top > SCREENRECT.height:
                self.kill()  # 画面外に出たらアイテムを消す
                self.spawned = False  # フラグをリセット
                
    def spawn(self) -> None:
        """
        アイテムを画面の左右にランダムで生成する。
        """
        side = random.choice(['left', 'right'])
        if side == 'left':
            self.rect.topleft = (0, random.randint(200, 280))
            self.speed = abs(self.speed)  # Move to the right
            
        else:
            self.rect.topright = (SCREENRECT.width, random.randint(200, 280))
            self.speed = -abs(self.speed)  # Move to the left
        self.spawned = True

    def is_spawned(self) -> bool:
        """
        アイテムが現在生成されているかどうかを確認する。
        戻り値: bool : アイテムが生成されていればTrue、そうでなければFalse。
        """
        return self.spawned

    def collide_bombs(self, bombs: pg.sprite.Group) -> bool:
        """
        爆弾との衝突を確認し、処理する。
        引数: bombs : pg.sprite.Group : 衝突を確認する爆弾のグループ。
        戻り値: bool : アイテムが爆弾と衝突した場合はTrue、そうでない場合はFalse。
        """
        global ALIEN_SCORE
        if self.spawned:
            collided = pg.sprite.spritecollide(self, bombs, True, pg.sprite.collide_mask)  # マスクを使用した衝突を確認
            if collided:
                self.kill()  # 衝突したらアイテムを消す
                ALIEN_SCORE += 1
                Alien.speed += 0.3
                self.spawned = False  # フラグをリセット
                self.rect.topleft = (-100, -100)  # 初期位置にリセット
                return True
        return False

    def collide_shots(self, shots: pg.sprite.Group) -> bool:
        """
        ショットとの衝突を確認し、処理する。
        引数: shots : pg.sprite.Group : 衝突を確認するショットのグループ。
        戻り値: bool : アイテムがショットと衝突した場合はTrue、そうでない場合はFalse。
        """
        global PLAYER_SCORE
        if self.spawned:
            collided = pg.sprite.spritecollide(self, shots, True, pg.sprite.collide_mask)  # マスクを使用した衝突を確認
            if collided:
                self.kill()
                PLAYER_SCORE += 1
                Player.speed += 0.3
                self.spawned = False  # 衝突したらフラグをリセット
                self.rect.topleft = (-100, -100)  # 画面外の初期位置にリセット
                return True
        return False

    def reset(self) -> None:
        """
        アイテムを初期状態にリセットする。
        """
        self.spawned = False # フラグをリセット
        self.rect.topleft = (-100, -100)  # 画面外に初期位置をリセット


class Win(pg.sprite.Sprite):
    """
    ・プレイヤーがエイリアンに爆弾を当てた際に画像と文字を呼び出す。
    ・エイリアンがプレイヤーに爆弾を当てた際に画像と文字を呼び出す。
    """
    def __init__(self, winner, *groups):
        pg.sprite.Sprite.__init__(self, *groups)
        self.image = pg.Surface(SCREENRECT.size)
        self.image.fill("black")
        
        if winner == "Player":
            win_image = load_image("player_win.png")
        else:
            win_image = load_image("alien_win.png")
        
        # この画像を小さくリサイズする
        win_image = pg.transform.scale(win_image, (SCREENRECT.width // 2, SCREENRECT.height // 4))
        
        # 勝利画像を黒い背景にブリットする
        win_image_rect = win_image.get_rect(center=(SCREENRECT.centerx, SCREENRECT.centery - 50))
        self.image.blit(win_image, win_image_rect)
        
        # 勝利テキストを描画する
        self.font = pg.font.Font(None, 50)
        self.color = "white"
        win_text = f"{winner} Wins!"
        text_surface = self.font.render(win_text, True, self.color)
        text_rect = text_surface.get_rect(center=(SCREENRECT.centerx, SCREENRECT.centery + 100))
        self.image.blit(text_surface, text_rect)
        
        self.rect = self.image.get_rect()


def main(winstyle=0):
    # Initialize pygame
    if pg.get_sdl_version()[0] == 2:
        pg.mixer.pre_init(44100, 32, 2, 1024)
    pg.init()
    if pg.mixer and not pg.mixer.get_init():
        print("Warning, no sound")
        pg.mixer = None

    fullscreen = False
    winstyle = 0  # |FULLSCREEN
    bestdepth = pg.display.mode_ok(SCREENRECT.size, winstyle, 32)
    screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)

    # Load images, assign to sprite classes
    img = load_image("3.png")
    Player.images = [img, pg.transform.flip(img, 1, 0)]
    img = load_image("explosion1.gif")
    Explosion.images = [img, pg.transform.flip(img, 1, 1)]
    Alien.images = [load_image(im) for im in ("alien1.gif", "alien2.gif", "alien3.gif")]
    Bomb.images = [load_image("bomb.gif")]
    Shot.images = [load_image("shot.gif")]
    Item.images = [load_image("item.png")]  # アイテム画像を読み込む

    icon = pg.transform.scale(Alien.images[0], (32, 32))
    pg.display.set_icon(icon)
    pg.display.set_caption("Pygame Aliens")
    pg.mouse.set_visible(0)

    bgdtile = load_image("utyuu.jpg")
    background = pg.Surface(SCREENRECT.size)
    background.blit(bgdtile, (0, 0))
    screen.blit(background, (0, 0))
    pg.display.flip()

    boom_sound = load_sound("enemy-attack.wav")
    shoot_sound = load_sound("fire-sword.wav")
    explosion_sound = load_sound("Explosion.wav")
    
    if pg.mixer:
        music = os.path.join(main_dir, "data", "game_music.mp3")
        pg.mixer.music.load(music)
        pg.mixer.music.play(-1)

    player = pg.sprite.Group()
    # players = pg.sprite.Group()
    aliens = pg.sprite.Group()
    shots = pg.sprite.Group()
    bombs = pg.sprite.Group()
    items = pg.sprite.Group()
    all = pg.sprite.RenderUpdates()

    global PLAYER_SCORE, ALIEN_SCORE
    player = Player(all)
    alien = Alien(aliens, all)
    
    all.add(player.gauge)  # プレイヤーのゲージを追加
    all.add(alien.gauge)  # エイリアンのゲージを追加

    aliens.add(alien)
    item = Item(items, all)  # アイテムを初期化し追加

    if pg.font:
        all.add(PlayerScore(all))
        all.add(AlienScore(all))
    
    item_timer = pg.time.get_ticks()
    clock = pg.time.Clock()

    while player.alive() and alien.alive():
        background.blit(bgdtile, (0, 0))
        screen.blit(background, (0, 0))
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                return
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_f:
                    if not fullscreen:
                        print("Changing to FULLSCREEN")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(SCREENRECT.size, winstyle | pg.FULLSCREEN, bestdepth)
                        screen.blit(screen_backup, (0, 0))
                    else:
                        print("Changing to windowed mode")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)
                        screen.blit(screen_backup, (0, 0))
                    pg.display.flip()
                    fullscreen = not fullscreen

        keystate = pg.key.get_pressed()

        all.clear(screen, background)
        all.update()

        direction = keystate[pg.K_RIGHT] - keystate[pg.K_LEFT]
        player.move(direction)
        
        player.gauge.update()
        player.gauge.increase()
        
        #pleyerのshotに関しての情報
        player_firing = keystate[pg.K_RETURN]
        player_spread = keystate[pg.K_l]
        player_shot_speed = keystate[pg.K_k]
        if not player.reloading and player_firing and len(shots) < MAX_SHOTS and player.gauge.can_fire():
            shot = Shot(player.gunpos(), 0, shots, all)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
            player.gauge.current_value -= 2
        elif not player.reloading and player_spread and len(shots) < MAX_SHOTS and PLAYER_SCORE >= 2 and player.gauge.spread_can_fire():#spread_shotが打てるようになる
            shot = Shot.spread_shot(player.gunpos(), shots, all, spread=15, count=3)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
            player.gauge.current_value -= 4
        elif not player.reloading and player_shot_speed and len(shots) < MAX_SHOTS and PLAYER_SCORE >= 4 and player.gauge.speed_can_fire():#speed_shotが打てるようになる
            shot = Speed_shot(player.gunpos(), 0, shots, all)
            if pg.mixer and shoot_sound is not None:
                shoot_sound.play()
            player.gauge.current_value -= 8
        player.reloading = player_firing

        direction = keystate[pg.K_d] - keystate[pg.K_a]
        alien.move(direction)
        
        alien.gauge.update()
        alien.gauge.increase()
        
        #alienのbombに関しての情報
        alien_firing = keystate[pg.K_t]
        alien_spread = keystate[pg.K_r]
        alien_shot_speed = keystate[pg.K_e]
        if not alien.reloading and alien_firing and len(bombs) < MAX_BOMBS and alien.gauge.can_fire():
            bomb = Bomb(alien.gunpos(), 0, bombs, all)
            if pg.mixer and shoot_sound is not None:
                boom_sound.play()
            alien.gauge.current_value -= 2
        elif not alien.reloading and alien_spread and len(bombs) < MAX_BOMBS and ALIEN_SCORE >= 2 and alien.gauge.spread_can_fire():#spread_shotが打てるようになる
            bomb = Bomb.spread_bomb(alien.gunpos(), bombs, all, spread=15, count=3)
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            alien.gauge.current_value -= 4
        elif not alien.reloading and alien_shot_speed and len(bombs) < MAX_BOMBS and ALIEN_SCORE >= 4 and alien.gauge.speed_can_fire():#speed_shotが打てるようになる
            bomb = Speed_bomb(alien.gunpos(), 0, bombs, all)
            if pg.mixer and boom_sound is not None:
                boom_sound.play()
            alien.gauge.current_value -= 8
        alien.reloading = alien_firing

        for shot in pg.sprite.spritecollide(alien, shots, 1, pg.sprite.collide_mask):
            Explosion(shot, all)
            Explosion(alien, all)
            if pg.mixer and boom_sound is not None:
                explosion_sound.play()
                pg.mixer.music.stop()
            all.add(Win("Player"))
            all.draw(screen)
            pg.display.flip()
            pg.time.wait(5000)
            alien.kill()
            return

        for bomb in pg.sprite.spritecollide(player, bombs, 1):
            Explosion(bomb, all)
            Explosion(player, all)
            if pg.mixer and boom_sound is not None:
                explosion_sound.play()
                pg.mixer.music.stop()
            player.kill()
            # Display win screen for alien
            all.add(Win("Alien"))
            all.draw(screen)
            pg.display.flip()
            pg.time.wait(5000)
            return
        
        all.add(player.gauge)  # プレイヤーのゲージを毎フレーム追加する
        all.add(alien.gauge)  # エイリアンのゲージを毎フレーム追加する

        # draw the scene
        dirty = all.draw(screen)
        pg.display.update(dirty)
        
        current_time = pg.time.get_ticks()
        if len(items) < MAX_ITEMS_ON_SCREEN and current_time - item_timer > ITEM_SPAWN_INTERVAL:
            new_item = Item(items, all)
            new_item.spawn()
            item_timer = current_time
        
        for item in items:
            if item.collide_bombs(bombs) or item.collide_shots(shots):
                item.kill()
                background.blit(bgdtile, (0, 0))
                screen.blit(background, (0, 0))
        
        pg.display.update(all.draw(screen))        
        clock.tick(40)
    if pg.mixer:
        pg.mixer.music.fadeout(1000)
    pg.time.wait(1000)


if __name__ == "__main__":
    main()
    pg.quit()
