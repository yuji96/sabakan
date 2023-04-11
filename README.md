# サーバー管理モニター

## 注意

- ブラウザでこのアプリのタブを複数開くと正常に動かないことがあります。

## ユーザの設定

1. ライブラリのインストール
   ```
   pip install git+https://github.com/yuji96/sabakan.git
   ```
2. 設定ファイル `~/.sabakan/config.yaml` を作成する。
   ```yaml
   ssh:
     user: username
     known_hosts_path: /home/username/.ssh/known_hosts
     private_key_path: /home/username/.ssh/your_private_key
   servers:
     foo:
       host: <ip address>
       gpustat: gpustat
       du_path: /home/.cache/sabakan/du.txt
     bar:
       host: <ip address>
       gpustat: gpustat
       du_path: /home/.cache/sabakan/du.txt
   ```
   - ホスト名（foo, bar）をキーとする。
   - gpustat のコマンドパスをホストごとに指定する。
   - du.txt のパスをホストごとに指定する。

## 管理者の設定

1. `gpustat` をインストールする。

   ```
   pip install gpustat
   ```

2. cron で `du, df` コマンドの定期実行の設定をする。

   ```
   # crontab -e
   0 5 * * * date > /home/.cache/sabakan/du.txt
   1 5 * * * df -h | grep home >> /home/.cache/sabakan/du.txt
   2 5 * * * du -hd 1 /home 2>/dev/null | sort -rh >> /home/.cache/sabakan/du.txt
   ```

3. du.txt の保存先を作成する。

   ```
   mkdir /home/.cache/sabakan
   ```
