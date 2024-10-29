import math
import os
import random
import sys
import time
import pygame as pg
from pygame.locals import *
import random
import math
import pygame as pg

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
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
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

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
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
                if key_lst[pg.K_LSHIFT]:
                    self.speed = 20
                else:
                    self.speed = 10
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)
        
        screen.blit(self.image, self.rect)

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird,angle0:float=0):  # angleのパラメータを追加
        """
        ビーム画像Surfaceを生成する
        引数1 bird：ビームを放つこうかとん
        引数2 angle0：追加の回転角度　（デフォルト：0）
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        angle += angle0  # 追加の回転角度を適用
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    複数方向ビームに関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        引数1 bird：ビームを放つこうかとん
        引数2 num：ビームの数
        """
        self.bird = bird
        self.num = num
    
    def gen_beams(self) -> list[Beam]:
        """
        複数方向のビームを生成する
        戻り値：Beamインスタンスのリスト
        """
        beams = []
        angle_range = 100  # -50度から+50度
        angle_step = angle_range / (self.num - 1) if self.num > 1 else 0
        
        for i in range(self.num):
            angle = -50 + (i * angle_step)  # -50度から+50度までの角度を計算
            beams.append(Beam(self.bird, angle))
        
        return beams

class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life
        self.image = pg.transform.rotozoom(pg.image.load("fig/images.jpg"), 0, 0.3)
        self.rect = self.image.get_rect()

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


# class Enemy(pg.sprite.Sprite):
#     """
#     敵機に関するクラス
#     """
#     imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
#     def __init__(self):
#         super().__init__()
#         self.image = random.choice(__class__.imgs)
#         self.rect = self.image.get_rect()
#         self.dir = random.randint(1, 4)
#         if self.dir == 1:  # 東に出現
#             self.rect.center = WIDTH, random.randint(0, HEIGHT)
#             self.vx, self.vy = -6, 0
#             self.bound = random.randint(WIDTH//2, WIDTH-50)  # 停止位置
#         elif self.dir == 2:  # 西に出現
#             self.rect.center = 0, random.randint(0, HEIGHT)
#             self.vx, self.vy = +6, 0
#             self.bound = random.randint(0, WIDTH//2)  # 停止位置
#         elif self.dir == 3:  # 南に出現
#             self.rect.center = random.randint(0, WIDTH), HEIGHT
#             self.vx, self.vy = 0, -6
#             self.bound = random.randint(HEIGHT//2, HEIGHT-50)  # 停止位置
#         elif self.dir == 4:  # 北に出現
#             self.rect.center = random.randint(0, WIDTH), 0
#             self.vx, self.vy = 0, +6
#             self.bound = random.randint(50, HEIGHT//2)  # 停止位置
#         self.state = "down"  # 降下状態or停止状態
#         self.interval = random.randint(50, 300)  # 爆弾投下インターバル

#     def update(self):
#         """
#         敵機を速度ベクトルself.vyに基づき移動（降下）させる
#         ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
#         引数 screen：画面Surface
#         """
#         if self.dir == 1:
#             if self.rect.centerx < self.bound:
#                 self.vx = 0
#                 self.vy = 0
#                 self.state = "stop"
#         if self.dir == 2:
#             if self.rect.centerx > self.bound:
#                 self.vx = 0
#                 self.vy = 0
#                 self.state = "stop"
#         if self.dir == 3:
#             if self.rect.centery < self.bound:
#                 self.vx = 0
#                 self.vy = 0
#                 self.state = "stop"
#         if self.dir == 4:
#             if self.rect.centery > self.bound:
#                 self.vx = 0
#                 self.vy = 0
#                 self.state = "stop"


#         self.rect.move_ip(self.vx, self.vy)

class Enemy(pg.sprite.Sprite):
    def __init__(self, player: Bird, spawn_directions: int):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/alien1.png"), 0, 0.5)
        self.rect = self.image.get_rect()
        self.image2 = pg.transform.rotozoom(pg.image.load("fig/images.jpg"), 0, 0.3)
        self.rect2 = self.image.get_rect()
        
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
import random
import math
import pygame as pg

class ClownEnemy(pg.sprite.Sprite):
    """ピエロの敵クラス"""
    def __init__(self, player: "Bird", spawn_directions: int):
        super().__init__()
        # 基本の画像設定
        self.image = pg.transform.rotozoom(pg.image.load("fig/images.jpg"), 0, 0.3)
        self.rect = self.image.get_rect()
        
        # 出現位置の設定（画面外から確実に出現するように修正）
        angle = random.randint(0, spawn_directions-1) * (360/spawn_directions)
        angle_rad = math.radians(angle)
        radius = 100  # 画面外からの距離を調整
        
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
        
       

# メインゲームループで使用する敵生成関数
def create_enemy(player: "Bird", spawn_directions: int) -> pg.sprite.Sprite:
    """敵を生成する関数"""
    return ClownEnemy(player, spawn_directions)



def main():
    pg.display.set_caption("こうかとんサバイバー")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravities = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    spawn_directions = 4  # 初期の出現方向数
    enemies_per_spawn = 1  # 初期の出現数
    last_enemy_increase = 0  # 最後に敵の数を増やした時間
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if tmr%70 == 0:  # 出現頻度を200から100に変更
                new_enemy = create_enemy(bird, spawn_directions)
                emys.add(new_enemy)
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_r and score.value >= 200:
                gravities.add(Gravity(400))  # 重力場を発動
                score.value -= 200  # スコアを消費

            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:  # 左シフトキーが押されている場合
                    # 複数方向ビームを発射
                    neo_beam = NeoBeam(bird, 5)  # 5本のビームを発射
                    beams.add(*neo_beam.gen_beams())
                else:
                    # 通常の単発ビーム
                    beams.add(Beam(bird))
        screen.blit(bg_img, [0, 0])

        # 5秒ごとに敵の出現数と方向を増やす
        current_time = tmr // 50  # フレーム数を秒数に変換
        if current_time - last_enemy_increase >= 5:
            enemies_per_spawn += 2  # 出現数を2増やす
            spawn_directions += 2   # 方向を2増やす
            last_enemy_increase = current_time

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy(bird, spawn_directions))

        # for emy in emys:
        #     if emy.state == "stop" and tmr%emy.interval == 0:
        #         # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
        #         bombs.add(Bomb(emy, bird))

        if pg.sprite.spritecollideany(bird, emys):
            return

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.groupcollide(bombs, gravities, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for emy in pg.sprite.groupcollide(emys, gravities, True, False).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ

        if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen, bird)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        gravities.update()
        gravities.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()