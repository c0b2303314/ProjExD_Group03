import math
import os
import random
import sys
import time
import pygame as pg
from pygame.locals import *


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))



def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate



def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm



class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life: int):
        """
        重力場Surfaceを生成する
        引数 life：重力場の発動時間
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.set_alpha(128)  # 透明度を設定
        self.image.fill((0, 0, 0))  # 黒い矩形
        self.rect = self.image.get_rect()
        self.life = life


    def update(self):
        """
        発動時間を1減算し、0未満になったら消滅する
        """
        self.life -= 1
        if self.life < 0:
            self.kill()



class GravityItem(pg.sprite.Sprite):
    """
    重力場発動アイテムに関するクラス
    """
    def __init__(self):
        """
        重力場発動アイテムを生成する
        """
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/bakudan.png"), 0, 0.15)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(50, WIDTH-50), random.randint(50, HEIGHT-50)  # 画面内にランダムでアイテムを出現させる



class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 1.25)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  # 追加: 通常状態
        self.hyper_life = 0    # 追加: 発動時間

        self.skills = []  # スキルの格納リスト(手持ちのスキル)
        self.wait_skill = False  # スキル選択画面の表示について


    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 1.25)
        screen.blit(self.image, self.rect)


    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)
        
        screen.blit(self.image, self.rect)



class Beam(pg.sprite.Sprite):
    """
    追尾機能付きビームに関するクラス
    """
    def __init__(self, bird: Bird, xbeam: float, enemies: pg.sprite.Group, clown_enemies: pg.sprite.Group, appearance):
        """
        ビームを生成する
        引数1 bird：ビームを放つこうかとん
        引数2 xbeam：ビーム倍率
        引数3 enemies：通常の敵機グループ
        引数4 clown_enemies：ピエロの敵機グループ
        """
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), 0, 2.0)
        self.rect = self.image.get_rect()
        self.rect.center = bird.rect.center
        self.speed = 10
        self.appearance = appearance
        
        if self.appearance:
            self.vx, self.vy = calc_orientation(self.rect, pg.Rect(WIDTH/2, 250, 0, 0))
        else:
            # 最も近い敵を特定
            self.target = self._find_nearest_enemy(bird, enemies, clown_enemies)
            # 初期の移動方向を設定
            self.vx, self.vy = bird.dire if self.target is None else calc_orientation(self.rect, self.target.rect)
        
        # 角度の計算と画像の回転
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, xbeam)


    def _find_nearest_enemy(self, bird: Bird, enemies: pg.sprite.Group, clown_enemies: pg.sprite.Group) -> pg.sprite.Sprite:
        """
        全ての敵（通常の敵とピエロ）の中から最も近い敵を見つける
        引数1 bird：こうかとん
        引数2 enemies：通常の敵機グループ
        引数3 clown_enemies：ピエロの敵機グループ
        戻り値：最も近い敵のSprite（敵がいない場合はNone）
        """
        nearest_enemy = None
        min_distance = float('inf')
        
        # 通常の敵とピエロの敵を両方チェック
        for enemy in list(enemies) + list(clown_enemies):
            distance = math.hypot(bird.rect.centerx - enemy.rect.centerx,
                                bird.rect.centery - enemy.rect.centery)
            if distance < min_distance:
                min_distance = distance
                nearest_enemy = enemy
        
        return nearest_enemy


    def update(self, xbeam: float, appearance):
        """
        ビームを移動させる
        敵が生存している場合は追尾する
        """
        if self.appearance:
            # ボスの中心座標を取得
            boss_centerx = appearance.rect.centerx
            boss_centery = appearance.rect.centery
            
            # ビームの現在座標を取得
            beam_centerx = self.rect.centerx
            beam_centery = self.rect.centery
            
            # ボスの中心座標への方向ベクトルを計算
            dx = boss_centerx - beam_centerx
            dy = boss_centery - beam_centery
            distance = math.sqrt(dx**2 + dy**2)  # 距離を計算
            
            if distance != 0:  # 0で割るのを防ぐ
                self.vx = dx / distance
                self.vy = dy / distance
            # 画面中央へ移動する処理
            self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        else:
            if self.target and self.target.alive():
                # ターゲットの方向を再計算
                self.vx, self.vy = calc_orientation(self.rect, self.target.rect)
                # 画像の角度を更新
                angle = math.degrees(math.atan2(-self.vy, self.vx))
                self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, xbeam)
            self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
            
        if (self.rect.centerx <= 0 or self.rect.centerx >= WIDTH) and (self.rect.centery <= 0 or self.rect.centery >= HEIGHT):
            self.kill()



class Bossbeam(pg.sprite.Sprite):
    """
    ボスビームに関するクラス
    """
    def __init__(self, boss, angle0:float=0):  # angleのパラメータを追加
        """
        ビーム画像Surfaceを生成する
        引数1 boss：ビームを放つボス
        引数2 angle0：追加の回転角度　（デフォルト：0）
        """
        super().__init__()
        self.vx, self.vy = boss.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        angle += angle0  # 追加の回転角度を適用
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = boss.rect.centery
        self.rect.centerx = boss.rect.centerx
        self.speed = 3


    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if (self.rect.centerx <= 0 or self.rect.centerx >= WIDTH) and (self.rect.centery <= 0 or self.rect.centery >= HEIGHT):
            self.kill()



class NeoBeam:
    """
    複数方向ビームに関するクラス
    """
    def __init__(self, boss, num: int):
        """
        引数1 boss：ビームを放つボス
        引数2 num：ビームの数
        """
        self.boss = boss
        self.num = num
    

    def gen_beams(self) -> list[Bossbeam]:
        """
        複数方向のビームを生成する
        戻り値：Beamインスタンスのリスト
        """
        beams = []
        # 基準となる角度をランダムに決定 (-180度から180度の間)
        base_angle = random.randint(-180, 180)
        angle_range = 100  # 発射範囲は100度
        angle_step = angle_range / (self.num - 1) if self.num > 1 else 0
        
        for i in range(self.num):
            # 基準角度を中心に扇状に広がるように角度を計算
            spread_angle = -50 + (i * angle_step)  # -50度から+50度まで扇状に広がる
            final_angle = base_angle + spread_angle  # 基準角度に扇状の角度を加算
            beams.append(Bossbeam(self.boss, final_angle))
        
        return beams
    


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Enemy", life: int):
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life


    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()



class Durian(pg.sprite.Sprite):
    """
    スキル:ドリアンのこと
    ドリアンに関するクラス
    引数1 player：ドリアンの初期位置をbirdの位置にする
    """
    def __init__(self, player: Bird):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load("fig/fruit_durian.png"), 0, 0.3)  # ドリアンの倍率設定
        self.rect = self.image.get_rect()
        self.rect.center = player.rect.center  # ドリアンの初期座標
        self.vx = 1  # 初期速度(x方向)
        self.vy = 1  # 初期速度(y方向)
        self.speed = 3
        self.has_damaged_boss = False  # Bossにダメージを与えたかどうかを示すフラグ


    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)

        if self.rect.left < 0:  # 左壁衝突時の反転
            self.vx *= -1
        if self.rect.right > WIDTH:  # 右壁衝突時の反転
            self.vx *= -1
        if self.rect.top < 0:  # 上壁衝突時の反転
            self.vy *= -1
        if self.rect.bottom > HEIGHT:  # 下壁衝突時の反転
            self.vy *= -1



class Soccerball(pg.sprite.Sprite):
    """
    サッカーボールに関するクラス
    引数1 player：ボールの初期位置をbirdの位置にする
    """
    def __init__(self, player: Bird):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load("fig/sport_soccerball.png"), 0, 0.1)  # サッカーボールの倍率設定
        self.rect = self.image.get_rect()
        self.rect.center = player.rect.center  # サッカーボールの初期座標
        self.vx = 1  # 初期速度(x方向)
        self.vy = 1  # 初期速度(y方向)
        self.speed = 10


    def update(self, emy_rct):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)

        if self.rect.left < 0 or self.rect.right > WIDTH:  # 左と右壁衝突時の反転
            self.vx *= -1
        if self.rect.top < 0 or self.rect.bottom > HEIGHT:  # 上と下壁衝突時の反転
            self.vy *= -1
        
    
        for emy in pg.sprite.spritecollide(self, emy_rct, False):
            if self.rect.left <= emy.rect.right or self.rect.right >= emy.rect.left:
                self.vx *= -1
            if self.rect.top >= emy.rect.bottom or self.rect.bottom <= emy.rect.top:
                self.vy *= -1



class Enemy(pg.sprite.Sprite):
    def __init__(self, player: Bird, spawn_directions: int):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/alien1.png"), 0, 0.5)
        self.rect = self.image.get_rect()
        
        # 指定された方向数に基づいてランダムな角度を選択
        angle = random.randint(0, spawn_directions-1) * (360/spawn_directions)
        angle_rad = math.radians(angle)
        radius = max(WIDTH, HEIGHT) + 100  # 画面外からの出現を確実にする
        
        self.rect.center = (
            WIDTH/2 + math.cos(angle_rad) * radius,
            HEIGHT/2 + math.sin(angle_rad) * radius
        )
        
        self.player = player
        self.speed = 3
        self.visible = False  # 画面内に入ったかどうかのフラグ


    def update(self):
        self.vx, self.vy = calc_orientation(self.rect, self.player.rect)
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)



class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50


    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)



class ClownEnemy(pg.sprite.Sprite):
    """ピエロの敵クラス"""
    def __init__(self, player: "Bird", spawn_directions: int):
        super().__init__()
        # 基本の画像設定
        self.image = pg.transform.rotozoom(pg.image.load("fig/images.jpg"), 0, 0.25)
        self.rect = self.image.get_rect()
        
        # 出現位置の設定（画面外から確実に出現するように修正）
        angle = random.randint(0, spawn_directions-1) * (360/spawn_directions)
        angle_rad = math.radians(angle)
        radius =max(WIDTH, HEIGHT) + 100  # 画面外からの距離を調整
        
        # 画面の中心からの位置を計算
        spawn_x = WIDTH/2 + math.cos(angle_rad) * radius
        spawn_y = HEIGHT/2 + math.sin(angle_rad) * radius
        
        # 画面外になるように調整
        if spawn_x < WIDTH/2:
            spawn_x = -50
        elif spawn_x >= WIDTH/2:
            spawn_x = WIDTH + 50
            
        if spawn_y < HEIGHT/2:
            spawn_y = -50
        elif spawn_y >= HEIGHT/2:
            spawn_y = HEIGHT + 50
            
        self.rect.center = (spawn_x, spawn_y)
        self.player = player
        self.base_speed = 2
        self.speed = self.base_speed
        self.points = 20
        
        # 移動用の変数
        self.vx = 0
        self.vy = 0
        self.movement_phase = 0


    def update(self):
        """敵の更新処理"""
        # プレイヤーへの方向を計算
        target_x = self.player.rect.centerx - self.rect.centerx
        target_y = self.player.rect.centery - self.rect.centery
        
        # 方向の正規化
        distance = math.sqrt(target_x**2 + target_y**2)
        if distance != 0:
            self.vx = (target_x / distance) * self.speed
            self.vy = (target_y / distance) * self.speed
            
        # ジグザグ動作の追加
        self.movement_phase += 0.1
        perpendicular_x = -self.vy  # 垂直方向のベクトル
        perpendicular_y = self.vx
        zigzag = math.sin(self.movement_phase) * 2  # ジグザグの振れ幅を調整
        
        # 最終的な移動を適用
        self.rect.x += self.vx + perpendicular_x * zigzag
        self.rect.y += self.vy + perpendicular_y * zigzag



class Item(pg.sprite.Sprite):
    """
    強化アイテムに関するクラス
    """
    def __init__(self):
        """
        強化アイテムSurfaceを生成する
        """
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/kouseki_colorful.png"), 0, 0.1)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(50, WIDTH-50), random.randint(50, HEIGHT-50)



class Boss:
    def __init__(self):
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/fantasy_dragon.png"), 0, 0.7)
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH/2, 0)  # ボスの初期位置を設定
        self.health = 300  # ボスの体力（必要に応じて調整）
        self.appearing=True
        self.font = pg.font.Font(None, 50)  # 体力表示用のフォント
        self.defeated = False  # ボス撃破フラグ
        self.defeat_time = None  # ボス撃破時刻
        self.dire=(+1, 0)


    def __update__(self, screen):
        # ボスの表示と移動
        if self.appearing:
            self.rect.y += 1
            if self.rect.top >= 150:
                self.rect.top = 150
                self.appearing = False

        # 体力表示
        health_text = self.font.render(f"Boss HP: {self.health}", True, (255, 0, 0))
        screen.blit(health_text, (10, 10))

        if self.health <= 1:
            self.health = 0

        # ボス撃破時の処理
        if self.health <= 0 and not self.defeated:
            self.defeated = True
            self.defeat_time = time.time()
            # 爆発エフェクトを生成
            explosion = Explosion(self, 100)
            health_text = self.font.render(f"Boss HP:", True, (255, 0, 0))
            return explosion
        
        # 通常表示
        if not self.defeated:
            screen.blit(self.image, self.rect)

        # ゲームクリア表示
        if self.defeated:
            clear_font = pg.font.Font(None, 150)
            clear_text = clear_font.render("GAME CLEAR!", True, (255, 215, 0))
            clear_rect = clear_text.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(clear_text, clear_rect)
            
            # 5秒経過後にゲーム終了
            if time.time() - self.defeat_time >= 5:
                pg.quit()
                sys.exit()

        

class Appearance:
    def __init__(self, score):
        self.score = score  # Score クラスのインスタンス
        self.boss_appeared = False  # ボスが登場しているかのフラグ
        self.boss = None  # ボスのインスタンス
        self.font = pg.font.Font(None, 100)
        self.boss_time = None
        self.flash_time = 0
        self.boss_visible = False


    def __update__(self, screen, emys, cemys):
        # ボスの出現条件
        if self.score.value >= 1000 and not self.boss_appeared:
            self.boss_appeared = True
            self.boss = Boss()
            for emy in emys:
                emy.kill()  # 他の敵を削除
            for cemy in cemys:
                cemy.kill()
            self.boss_time = time.time()  # 通常の敵をすべて削除
            self.flash_time = 0  # 点滅時間リセット
            self.boss_visible = False  # 点滅状態に入る前に初期化

        # ボスが登場している場合の更新と表示
        if self.boss_time and time.time() - self.boss_time < 4:
            # ボス襲来の文字表示
            self.flash_time += 1
            if self.flash_time % 80 < 10:
                text = self.font.render("WARNING!!", True, (255, 0, 0))
                screen.blit(text, (320, HEIGHT / 2))
                if self.flash_time > 4:
                    self.boss_visible = True
        elif self.boss and self.boss_visible:
            # ボスが点滅状態を抜けた後も表示
            self.boss.__update__(screen)


        
def main():
    pg.display.set_caption("こうかとんサバイバー")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    level_save = 0

    bird = Bird(3, (900, 400))
    beams = pg.sprite.Group()
    boss_beams=pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    cemys = pg.sprite.Group()
    gravities = pg.sprite.Group()
    items = pg.sprite.Group()
    gravityitems = pg.sprite.Group()
    drns = pg.sprite.Group()  # ドリアンのグループ
    balls = pg.sprite.Group()  # サッカーボールのグループ
    appearance=Appearance(score)
    

    tmr = 0
    beam_timer = 0  # 追加: ビーム発射のタイマー
    clock = pg.time.Clock()
    spawn_directions = 4  # 初期の出現方向数
    enemies_per_spawn = 3  # 初期の出現数
    last_enemy_increase = 0  # 最後に敵の数を増やした時間
    xbeam = 1.0  # 初期のビーム倍率
    beam_span = 0  # ビーム発射のスパン
    item_count = 0  # アイテム獲得数

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            """
            スキル選択画面
            敵を倒した数で判断
            選択画面表示中はすべての時間をSTOPする
            キーボードでスキルの選択:
                1 ドリアン
                2 サッカーボール
            """
            if bird.wait_skill:  # birdで定義、スキル画面のこと
                if event.type == pg.KEYDOWN:  # キーが押されたら
                    if event.key == pg.K_1:  # 1を押したら
                        drns.add(Durian(bird))  # スキルのリストに、クラス(Durian)を追加
                        bird.wait_skill = False  # この画面を消す
                    if event.key == pg.K_2:  #2を押したら
                        balls.add(Soccerball(bird))  # スキルリストに、クラス(Soccerball)を追加
                        bird.wait_skill = False  # この画面を消す

        # 定期的に自動発射
        beam_timer += 1
        if beam_span >= 29:
            beam_span = 29
        if beam_timer % (30 - beam_span) == 0:  # 30フレームごとにビームを自動発射
            beams.add(Beam(bird, xbeam ,emys ,cemys, appearance.boss_appeared))  # emysグループを渡す
            beam_timer = 0  # タイマーをリセット

        screen.blit(bg_img, [0, 0])

        # 5秒ごとに敵の出現数と方向を増やす
        current_time = tmr // 50  # フレーム数を秒数に変換
        if current_time - last_enemy_increase >= 5 and not appearance.boss_appeared:
            enemies_per_spawn += 100  # 出現数を2増やす
            spawn_directions += 2   # 方向を2増やす
            last_enemy_increase = current_time

        if tmr%20 == 0 and not appearance.boss_appeared: # 20フレームに1回，敵機を出現させる
            emys.add(Enemy(bird, spawn_directions))

        if tmr%100 == 0 and not appearance.boss_appeared:
            cemys.add(ClownEnemy(bird, spawn_directions))

        if tmr != 0:
            if tmr%100 == 0:  # 100フレームに1回、強化アイテムを出現させる
                items.add(Item())

        if tmr != 0:
            if tmr%1000 == 0:  # 1000フレームに1回、重力場発動アイテムを出現させる
                gravityitems.add(GravityItem())

        if tmr%100 == 0 and appearance.boss_appeared:
            boss_neo_beam = NeoBeam(appearance.boss, 3)  # ボスが3本のビームを発射
            boss_beams.add(boss_neo_beam.gen_beams())

        # 通常の敵との衝突判定
        if pg.sprite.spritecollideany(bird, emys):
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        # ピエロとの衝突判定
        if pg.sprite.spritecollideany(bird, cemys):
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

            if int(score.value / 150) > level_save:  # 150点ごとにスキルの選択
                bird.wait_skill = True
                level_save = int(score.value / 150)

        if bird.wait_skill:
            """
            スキル選択画面
            """
            screen.fill((0, 0, 0))  # 黒画面
            font = pg.font.Font(None, 50)  # fontの大きさ
            text = font.render("Select Skill - 1:Durian 2:Soccerball", True, (255, 255, 255))  # 書く文字と白色
            screen.blit(text, ((WIDTH//4) - 75, HEIGHT//2))  # 描写位置
            pg.display.update()
            continue  # これがないと下のアップデートが実行されてしまうため必須

        for emy in pg.sprite.groupcollide(emys, drns, True, False).keys():
            exps.add(Explosion(emy, 100))
            score.value += 5

        for emy in pg.sprite.groupcollide(cemys, drns, True, False).keys():
            exps.add(Explosion(cemy, 100))
            score.value += 5

        balls.update(emys)  # 反射のみ
        balls.update(cemys)  # 反射のみ
        

        for emy in pg.sprite.groupcollide(emys, balls, True, False).keys():
            exps.add(Explosion(emy, 100))
            score.value += 5

        for emy in pg.sprite.groupcollide(cemys, balls, True, False).keys():
            exps.add(Explosion(cemy, 100))
            score.value += 5

        for cemy in pg.sprite.groupcollide(cemys, beams, True, True).keys():
            exps.add(Explosion(cemy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
            if int(score.value / 150) > level_save:  # 150点ごとにスキルの選択
                bird.wait_skill = True
                level_save = int(score.value / 150)

        for emy in pg.sprite.groupcollide(emys, gravities, True, False).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ

        for cemy in pg.sprite.groupcollide(cemys, gravities, True, False).keys():
            exps.add(Explosion(cemy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ

        for item in pg.sprite.spritecollide(bird, items, True):  # こうかとんと強化アイテムがぶつかったら
            xbeam += 0.2  # ビームの倍率をあげる
            score.value += 10  # 10点アップ
            if bird.speed <= 20:  # こうかとんのスピードの最大値を設定
                bird.speed *= 1.1 
            item_count += 1
            if item_count % 2 == 0:  # ２回に一回、アイテムを獲得するとビームのスパンをあげる
                beam_span += 1
            item.kill()  # 強化アイテムを削除する

        for gitem in pg.sprite.spritecollide(bird, gravityitems, True):  # こうかとんと重力場発動アイテムがぶつかったら
            gravities.add(Gravity(80))
            if appearance.boss_appeared:  # もしボスが現れている場合
                appearance.boss.health -= 20  # 20ダメージを与える
            gitem.kill()  # 重力場発動アイテムを削除する
        
        if len(pg.sprite.spritecollide(bird, boss_beams, True)) != 0:
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return
        
        if appearance.boss and appearance.boss_visible:
            for beam in beams:
                if appearance.boss.rect.colliderect(beam.rect):
                    appearance.boss.health -= 1  # ビームが当たるたびに体力を1減らす
                    beam.kill()  # ビームを消す
            for drn in drns:
                if appearance.boss.rect.colliderect(drn.rect):
                    if not drn.has_damaged_boss:  # まだダメージを与えていない場合
                        appearance.boss.health -= 1  
                        drn.has_damaged_boss = True 
                else:
                    drn.has_damaged_boss = False # Bossと接触していない間はフラグをFalseに戻す
            for ball in balls:
                if appearance.boss.rect.colliderect(ball.rect):
                    # ボールのx方向の中心とBossのx方向の中心の差の絶対値
                    dx = abs(ball.rect.centerx - appearance.boss.rect.centerx)  
                    # ボールのy方向の中心とBossのy方向の中心の差の絶対値
                    dy = abs(ball.rect.centery - appearance.boss.rect.centery)  

                    if dx > dy:  # 左右の衝突 (x方向の差が大きい)
                        ball.vx *= -1  # x方向の速度を反転
                    else:  # 上下の衝突 (y方向の差が大きい)
                        ball.vy *= -1  # y方向の速度を反転

                    if ball.rect.centerx > appearance.boss.rect.left and ball.rect.centerx < appearance.boss.rect.right and ball.rect.centery > appearance.boss.rect.top and ball.rect.centery < appearance.boss.rect.top:
                        ball.rect.right = appearance.boss.rect.left - 50  #  ボールがボスにめり込んだ場合外に出す
                    appearance.boss.health -= 1  # ボールが当たるたびに体力を1減らす
                    
                    
            # ボス撃破時の爆発エフェクト生成
            explosion = appearance.boss.__update__(screen)
            if explosion:
                exps.add(explosion)
        

        

        bird.update(key_lst, screen)
        beams.update(xbeam, appearance.boss)
        beams.draw(screen)
        boss_beams.update()
        boss_beams.draw(screen)
        emys.update()
        emys.draw(screen)
        exps.update()
        exps.draw(screen)
        gravities.update()
        gravities.draw(screen)
        drns.update()
        drns.draw(screen)
        balls.draw(screen)  # スキル機能の描画
        items.draw(screen)  # 強化アイテムを画面に描画
        gravityitems.draw(screen)  # 重力場発動アイテムを画面に描画
        score.update(screen)
        cemys.update()
        cemys.draw(screen)
        appearance.__update__(screen, emys, cemys)
        
        pg.display.update()
        tmr += 1
        clock.tick(50)
        
        

if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
