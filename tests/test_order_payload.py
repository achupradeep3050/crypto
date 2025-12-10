import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from backend.strategy_engine import StrategyEngine

class TestOrderPayload(unittest.IsolatedAsyncioTestCase):
    async def test_execute_trade_sends_market_order(self):
        # Setup
        engine = StrategyEngine(name="TestBot", mode="15m1m", log_file="test.log")
        engine.agent_url = "http://mock-agent:8001"
        
        # Mock Session
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"retcode": 0})
        mock_response.__aenter__.return_value = mock_response

        # Mock Risk Manager to return valid qty
        engine.risk_manager.calculate_lot_size = MagicMock(return_value=0.1)

        # Execute
        with patch('aiohttp.ClientSession.post', return_value=mock_response) as mock_post:
            with patch('aiohttp.ClientSession.get', return_value=mock_response): # Account info mock
                async with asyncio.Lock(): # dummy context
                    # manually call execute_trade with a session
                    # We need to simulate the session context manager in execute_trade?
                    # execute_trade takes 'session' as arg.
                    
                    mock_session = MagicMock()
                    mock_session.post.return_value = mock_response
                    mock_session.get.return_value = mock_response
                    
                    # Call with explicit order_type="market" (which is now default, but testing explicit)
                    await engine.execute_trade(mock_session, "BTCUSD", "long", 50000, 49000, 52000, order_type="market")
                    
                    # Verify
                    mock_session.post.assert_called_once()
                    args, kwargs = mock_session.post.call_args
                    
                    url = args[0]
                    payload = kwargs['json']
                    
                    print(f"URL: {url}")
                    print(f"Payload: {payload}")
                    
                    self.assertEqual(payload['order_type'], "market")
                    self.assertEqual(payload['action'], "buy")
                    self.assertEqual(payload['price'], 50000) # It sends price, but Agent ignores it for market

    async def test_execute_trade_default_is_market(self):
        # Setup
        engine = StrategyEngine(name="TestBot", mode="15m1m", log_file="test.log")
        
        mock_response = MagicMock()
        mock_response.status = 200
        engine.risk_manager.calculate_lot_size = MagicMock(return_value=0.1)

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_session.get.return_value = mock_response
        mock_response.__aenter__.return_value = mock_response

        # Call WITHOUT order_type arg
        await engine.execute_trade(mock_session, "BTCUSD", "long", 50000, 49000, 52000)
        
        args, kwargs = mock_session.post.call_args
        payload = kwargs['json']
        
        self.assertEqual(payload['order_type'], "market", "Default order type should be market")

if __name__ == '__main__':
    unittest.main()
