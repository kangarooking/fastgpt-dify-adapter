# fastgpt-dify-adapter
dify外接fastgpt知识库的工具

使用方式参考：https://mp.weixin.qq.com/s/crQrneHZ0sT-c04YanofSw

## 生成随机 API Key

```shell
echo "sk-$(openssl rand -hex 16)"
echo "sk-$(openssl rand -base64 16 | tr -d '/+=')"
echo "sk-$(uuidgen | tr -d '-')"
echo "sk-$(date +%s | md5sum | cut -c1-32)"
echo "sk-$(echo $RANDOM$(date +%s) | sha256sum | cut -c1-32)"
# API_KEY=sk-u52DLfEleq1Outn1q2Hgg
```
