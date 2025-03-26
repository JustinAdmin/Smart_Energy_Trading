// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// Vickrey auction contract
contract EnergyVickreyAuction {
    struct Bid {
        bytes32 sealedBid;
        uint256 deposit;
    }

    address public seller;
    uint256 public biddingStart;
    uint256 public biddingEnd;
    uint256 public revealEnd;
    bool public ended;
    uint256 public biddingDuration; // Bidding phase duration
    uint256 public revealDuration;  // Reveal phase duration

    mapping(address => Bid) public bids;
    address[] public bidders;

    address public highestBidder;
    uint256 public highestBid;
    uint256 public secondHighestBid;

    uint256 public energyAmount;

    event BidPlaced(address indexed bidder, uint256 deposit);
    event BidRevealed(address indexed bidder, uint256 value);
    event AuctionEnded(address winner, uint256 winningBid);
    event AuctionReset();
    event RevealDebug(
        address bidder,
        bytes32 providedHash,
        bytes32 computedHash,
        uint256 value,
        string nonce
    );

    modifier onlyBefore(uint256 _time) {
        require(block.timestamp < _time, "Too late");
        _;
    }

    modifier onlyAfter(uint256 _time) {
        require(block.timestamp > _time, "Too early");
        _;
    }

    modifier auctionNotEnded() {
        require(!ended, "Auction already ended");
        _;
    }

    modifier onlySeller() {
        require(msg.sender == seller, "Only the seller can perform this action");
        _;
    }

    constructor(uint256 _biddingDuration, uint256 _revealDuration) {
        seller = msg.sender;
        biddingDuration = _biddingDuration;
        revealDuration = _revealDuration;
    }

    function getBidders() external view returns (address[] memory) {
        return bidders;
    }

    function getBidDeposits() external view returns (address[] memory, uint256[] memory) {
        if (bidders.length == 0) {
            return (new address[](0), new uint256[](0));  // Fixed empty array initialization
        }

        uint256[] memory deposits = new uint256[](bidders.length);

        for (uint256 i = 0; i < bidders.length; i++) {
            deposits[i] = bids[bidders[i]].deposit;
        }

        return (bidders, deposits);
    }


    // Start the auction with correct timing logic
    function startAuction(uint256 _value) external {
        require(biddingStart == 0, "Auction has already started");
        biddingStart = block.timestamp;
        biddingEnd = biddingStart + biddingDuration;
        revealEnd = biddingEnd + revealDuration;
        energyAmount = _value;
        seller = msg.sender;
    }

    // Place bid
    function bid(bytes32 _sealedBid) external payable onlyBefore(biddingEnd) {
        require(bids[msg.sender].sealedBid == bytes32(0), "Already bid");
        require(msg.value > 0, "Deposit must be greater than 0");

        bids[msg.sender] = Bid({
            sealedBid: _sealedBid,
            deposit: msg.value
        });
        bidders.push(msg.sender);

        emit BidPlaced(msg.sender, msg.value);
    }

    // Reveal bids
    function reveal(uint256 _value, string calldata _nonce)
        external
        onlyAfter(biddingEnd)
        onlyBefore(revealEnd)
    {
        Bid storage bidToCheck = bids[msg.sender];
        require(bidToCheck.sealedBid != bytes32(0), "No bid found");

        // Compute hash the same way as in the bid
        bytes32 computedHash = keccak256(abi.encodePacked(_value, _nonce));
        
        // Emit debug event
        emit RevealDebug(
            msg.sender,
            bidToCheck.sealedBid,
            computedHash,
            _value,
            _nonce
        );

        require(
            bidToCheck.sealedBid == computedHash,
            "Invalid bid reveal"
        );
        require(bidToCheck.deposit >= _value, "Deposit too low");

        // Update highest and second highest bids
        if (_value > highestBid) {
            secondHighestBid = highestBid;
            highestBid = _value;
            highestBidder = msg.sender;
        } else if (_value > secondHighestBid && msg.sender != highestBidder) {
            secondHighestBid = _value;
        }

        emit BidRevealed(msg.sender, _value);
    }

    // Finalize auction (manual close by auctioneer)
    function closeAuction() external onlySeller auctionNotEnded {
        require(block.timestamp >= biddingEnd, "Bidding phase is not over");

        ended = true;

        // Finalize the auction by transferring funds
        if (highestBidder != address(0)) {
            payable(seller).transfer(secondHighestBid);
            payable(highestBidder).transfer(
                bids[highestBidder].deposit - secondHighestBid
            );
        }

        // Refund non-winners
        for (uint256 i = 0; i < bidders.length; i++) {
            address bidder = bidders[i];
            if (bidder != highestBidder) {
                uint256 refundAmount = bids[bidder].deposit;
                bids[bidder].deposit = 0;
                if (refundAmount > 0) {
                    payable(bidder).transfer(refundAmount);
                }
            }
        }

        emit AuctionEnded(highestBidder, secondHighestBid);
    }

    // Reset auction
    function resetAuction(uint256 _biddingDuration, uint256 _revealDuration) external onlySeller {
        require(ended, "Auction must be ended before resetting");

        biddingStart = 0;
        biddingEnd = block.timestamp + _biddingDuration;
        revealEnd = biddingEnd + _revealDuration;
        ended = false;
        highestBidder = address(0);
        highestBid = 0;
        secondHighestBid = 0;

        for (uint256 i = 0; i < bidders.length; i++) {
            delete bids[bidders[i]];
        }
        delete bidders;

        emit AuctionReset();
    }
}
